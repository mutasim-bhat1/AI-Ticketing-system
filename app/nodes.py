import json
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from app.state import TicketState


class WorkflowNodes:
    """
    Workflow nodes for the agentic ticketing system.

    KEY CHANGE: Instead of hardcoded nodes that call tools in a fixed order,
    we now have a single 'agent_node' that runs a ReAct loop —
    the LLM AUTONOMOUSLY decides which tools to call, in what order,
    and when to stop.
    """

    def __init__(self, llm, tools, config: dict):
        self.llm = llm
        self.tools = tools
        self.tool_map = {t.name: t for t in tools}          # name -> tool function
        self.llm_with_tools = llm.bind_tools(tools, parallel_tool_calls=False)  # One tool at a time (more reliable with Groq)
        self.config = config

    # ─── Node 1: Extract Intents (Structural — keeps the multi-intent capability) ───

    def extract_intents_node(self, state: TicketState) -> dict:
        """Extracts distinct support intents from the query."""
        print(f"[NODE] Extracting intents from: {state['original_query'][:50]}...")

        prompt = f"""You are an intent extraction assistant.
Analyze the user's query and extract distinct, independent requests or topics.

**CRITICAL RULES:**
1. Extract ALL intents — whether they are support requests, general questions, or casual messages.
2. If the query is about ONE single topic, return ONLY one intent.
3. Only split if the user explicitly asks for two or more different things.
4. For greetings like "Hi" or "Hello", return ["greeting"].
5. For nonsense/gibberish, return the original text as a single intent.

User Query: "{state['original_query']}"

Response Format (JSON only):
{{
  "intents": ["intent 1"]
}}
"""
        response = self.llm.invoke([SystemMessage(content=prompt)])
        try:
            content = response.content.replace("```json", "").replace("```", "").strip()
            data = json.loads(content)
            return {"intents": data["intents"], "current_intent_index": 0}
        except Exception as e:
            print(f"Error parsing intents: {e}")
            return {"intents": [state["original_query"]], "current_intent_index": 0}

    # ─── Node 2: Intent Router (Structural — loops through intents) ────────────────

    def intent_router_node(self, state: TicketState) -> dict:
        """Iteratively sets the next intent to process."""
        idx = state.get("current_intent_index", 0)
        intents = state.get("intents", [])

        if idx < len(intents):
            current = intents[idx]
            print(f"\n[NODE] Processing Intent {idx+1}/{len(intents)}: {current}")
            return {"current_intent": current}
        return {"current_intent": None}

    # ─── Node 3: THE AGENTIC NODE — LLM decides everything ────────────────────────

    def agent_node(self, state: TicketState) -> dict:
        """
        🧠 THE CORE AGENTIC LOOP (ReAct Pattern)

        This is where the magic happens. Instead of hardcoded tool calls:
          OLD: search_kb → if/else → send_email → generate_reply  (FIXED order)
          NEW: LLM decides → calls tool → observes result → decides next → ... (AUTONOMOUS)

        The LLM has access to all tools and CHOOSES:
        - WHICH tools to call
        - In WHAT ORDER
        - HOW MANY TIMES
        - WHEN to stop
        """
        intent = state["current_intent"]
        original_query = state["original_query"]

        print(f"\n🤖 [AGENT] Starting autonomous processing for: '{intent}'")

        # ── Build the agent's initial messages ──
        system_prompt = SystemMessage(content=f"""You are an intelligent support agent AND a helpful chatbot. Your job is to autonomously process a user's request using the tools available to you.

CURRENT INTENT: {intent}
ORIGINAL QUERY: {original_query}

YOUR TOOLS:
1. search_kb(query) — Search the knowledge base for matching services.
2. generate_reply(query, service, department) — Generate a helpful support response.
3. send_email(email, subject, body) — Send a ticket email.
4. escalate(reason) — Escalate to human review.
5. chat(query) — Answer general questions directly (no tickets, no emails).

MANDATORY WORKFLOW & RULES:
1. FIRST: Decide if this is a SUPPORT REQUEST or a GENERAL QUERY.
   - Support requests: IT issues, password resets, fee payments, library, transport, academics, complaints, etc.
   - General queries: greetings, casual chat, general knowledge questions, nonsense, etc.

2. IF GENERAL QUERY or NONSENSE: Call chat(query). Do NOT call search_kb, send_email, or escalate. STOP after chat returns.

3. IF SUPPORT REQUEST: Follow the full workflow:
   Step A: Call search_kb(query) to find the matching service.
   Step B: Read the result — use the EXACT email, service, and department from the result.
   Step C: Call send_email with the EXACT email from search_kb. NEVER invent an email.
   Step D: Call generate_reply with the EXACT service and department from search_kb.
   Step E: STOP. Do NOT write your own summary.

4. If search_kb finds no match: call escalate(reason="...") and send_email to {self.config['general_support_email']}. Then call generate_reply.

**CRITICAL RESPONSE RULES — READ CAREFULLY:**
- NEVER mention tool names (search_kb, generate_reply, send_email, escalate, chat) in your response.
- NEVER describe which functions you called or the internal steps you took.
- NEVER say things like "The search_kb function was called" or "I called the send_email function".
- After calling all required tools, simply STOP. Do NOT write a summary of what tools you used.
- The generate_reply or chat tool will produce the user-facing response. You do NOT need to add anything.
- If you must write a final message, make it SHORT and conversational — like a human support agent would.
- BAD example: "The search_kb function was called and found a match. The send_email function was called to send a ticket."
- GOOD example: "Your request has been forwarded to the IT Support team. You'll hear back shortly!"
""")

        human_msg = HumanMessage(content=f"Please process this support request: {intent}")
        messages = [system_prompt, human_msg]

        # ── Tracking variables ──
        tickets = list(state.get("tickets_created", []))
        responses = list(state.get("responses", []))
        reply_generated = False

        # ── The ReAct Loop — LLM reasons, acts, observes, repeats ──
        MAX_ITERATIONS = 8
        api_failed = False

        for iteration in range(MAX_ITERATIONS):
            print(f"  🔄 [AGENT] Iteration {iteration + 1}/{MAX_ITERATIONS}")

            # 1. Ask the LLM what to do next
            try:
                response = self.llm_with_tools.invoke(messages)
                messages.append(response)
            except Exception as e:
                # Groq API tool-calling can be flaky — retry once
                print(f"  ⚠️ [AGENT] Tool-calling error (attempt 1): {e}")
                try:
                    import time
                    time.sleep(1)  # Brief pause before retry
                    response = self.llm_with_tools.invoke(messages)
                    messages.append(response)
                except Exception as e2:
                    print(f"  ❌ [AGENT] Tool-calling failed on retry: {e2}")
                    api_failed = True
                    break

            # 2. If no tool calls → the agent is DONE
            if not response.tool_calls:
                print(f"  ✅ [AGENT] Finished. Final message: {response.content[:100]}...")
                # If the agent never called generate_reply, use its final text
                if not reply_generated and response.content:
                    responses.append(f"Regarding '{intent}': {response.content}")
                break

            # 3. Execute each tool the LLM chose to call
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                print(f"  🔧 [AGENT] Chose tool: {tool_name}({json.dumps(tool_args, default=str)[:120]})")

                # Execute the tool
                tool_fn = self.tool_map.get(tool_name)
                if tool_fn:
                    try:
                        result = tool_fn.invoke(tool_args)
                    except Exception as e:
                        result = f"Tool execution failed: {str(e)}"
                        print(f"  ❌ [AGENT] Tool error: {e}")
                else:
                    result = f"Error: Unknown tool '{tool_name}'"

                print(f"  📋 [AGENT] Tool result: {str(result)[:120]}...")

                # Track side effects
                if tool_name == "send_email":
                    tickets.append({
                        "intent": intent,
                        "email": tool_args.get("email", "unknown"),
                        "service": tool_args.get("subject", "Support Request"),
                        "log": str(result)
                    })

                if tool_name == "generate_reply":
                    responses.append(f"Regarding '{intent}': {result}")
                    reply_generated = True

                if tool_name == "chat":
                    responses.append(result)
                    reply_generated = True

                # 4. Feed the tool result BACK to the LLM so it can reason about it
                messages.append(
                    ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                )

        else:
            # Safety: if we hit max iterations without the LLM stopping
            print(f"  ⚠️ [AGENT] Hit max iterations ({MAX_ITERATIONS})")
            api_failed = not reply_generated  # Trigger fallback if no reply was generated

        # ── FALLBACK: If the LLM tool-calling API failed, execute tools programmatically ──
        if api_failed and not reply_generated:
            print(f"  🔧 [AGENT] Running deterministic fallback for: '{intent}'")
            try:
                # Step 1: Search KB to determine if this is a real support request
                kb_result = self.tool_map["search_kb"].invoke({"query": intent})
                confidence = kb_result.get("confidence", 0) if "error" not in kb_result else 0

                if "error" not in kb_result and confidence >= 0.5:
                    # HIGH confidence KB match → this IS a support request → ticket workflow
                    email_addr = kb_result.get("email", self.config["general_support_email"])
                    service = kb_result.get("service", "General Support")
                    department = kb_result.get("department", "General Support")

                    email_res = self.tool_map["send_email"].invoke({
                        "email": email_addr,
                        "subject": f"New Ticket: {service}",
                        "body": f"User Intent: {intent}\nOriginal Query: {original_query}"
                    })
                    tickets.append({"intent": intent, "email": email_addr, "service": service, "log": str(email_res)})

                    reply = self.tool_map["generate_reply"].invoke({
                        "query": intent, "service": service, "department": department
                    })
                    responses.append(f"Regarding '{intent}': {reply}")
                else:
                    # LOW confidence or no match → NOT a support request → use chat tool
                    print(f"  💬 [AGENT] Low KB confidence ({confidence}) — treating as general query")
                    if "chat" in self.tool_map:
                        chat_result = self.tool_map["chat"].invoke({"query": original_query})
                        responses.append(chat_result)
                    else:
                        responses.append("I'm sorry, I couldn't find a matching service for your request. Please try rephrasing or contact general support.")
            except Exception as fallback_err:
                print(f"  ❌ [AGENT] Fallback also failed: {fallback_err}")
                responses.append(f"Regarding '{intent}': We encountered an issue processing your request. Please try again later.")

        print(f"🤖 [AGENT] Complete for intent: '{intent}'")

        return {
            "tickets_created": tickets,
            "responses": responses,
            "current_intent_index": state["current_intent_index"] + 1
        }

    # ─── Node 4: Aggregate (Structural — combines all responses) ───────────────────

    def aggregate_node(self, state: TicketState) -> dict:
        """Merges all responses into a final, clean, user-friendly message."""
        if not state["responses"]:
            return {"final_response": "Hello! I'm here to help. You can ask me general questions or submit support requests for IT, Finance, Library, Transport, or Academic services."}

        # Clean responses: remove any that are just agent narration about tool calls
        tool_keywords = ["search_kb", "generate_reply", "send_email", "escalate", "chat(", "function was called", "function did not", "tool_call", "tool call"]
        clean_responses = []
        for r in state["responses"]:
            # Skip responses that are just the agent narrating its own tool usage
            r_lower = r.lower()
            is_narration = any(kw in r_lower for kw in tool_keywords)
            if not is_narration:
                clean_responses.append(r)

        # If all responses were narration, use the original but strip tool references
        if not clean_responses:
            clean_responses = state["responses"]

        summary = "\n\n".join(clean_responses)

        # Strip any remaining tool name mentions from the final text
        import re
        summary = re.sub(r'\b(search_kb|generate_reply|send_email|escalate|chat)\s*\(', '', summary)
        summary = re.sub(r'\bthe\s+(search_kb|generate_reply|send_email|escalate|chat)\s+function\b', 'the system', summary, flags=re.IGNORECASE)

        if state.get("tickets_created"):
            final = f"{summary}\n\nThank you for reaching out!"
        else:
            final = summary

        return {"final_response": final}
