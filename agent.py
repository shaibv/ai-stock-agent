from openai import OpenAI
import json
import re
from tools import TOOLS, TOOL_FUNCTIONS

client = OpenAI()

DAILY_API_CAP = 200


def run_agent(system_prompt: str, previous_portfolio: dict | None, api_counter: dict) -> tuple[dict, int]:
    """
    Run one agent's tool-calling loop until it produces a portfolio.

    Args:
        system_prompt: The agent's personality/strategy prompt (with {previous_portfolio} placeholder).
        previous_portfolio: The agent's portfolio from yesterday, or None on Day 1.
        api_counter: Mutable dict {"calls": int} shared across agents to enforce the daily cap.

    Returns:
        (portfolio_dict, api_calls_used)
    """
    prev_str = json.dumps(previous_portfolio, indent=2) if previous_portfolio else "This is Day 1 — no previous portfolio. Build from scratch."
    filled_prompt = system_prompt.format(previous_portfolio=prev_str)

    if previous_portfolio:
        user_message = (
            "Review your current portfolio (shown in the system prompt) and today's "
            "Reddit activity + stock data. Decide whether to rebalance or hold. "
            "Remember: each trade costs $3. Only change positions if the expected "
            "gain justifies the cost. Output your final portfolio as JSON."
        )
    else:
        user_message = (
            "Build me a stock portfolio starting from $100,000 cash. Research Reddit "
            "for trending stocks, validate with real market data, and output your "
            "portfolio as JSON."
        )

    messages = [
        {"role": "system", "content": filled_prompt},
        {"role": "user", "content": user_message},
    ]

    calls_used = 0

    for iteration in range(50):

        if api_counter["calls"] >= DAILY_API_CAP:
            messages.append({
                "role": "user",
                "content": "API budget exhausted. You MUST output your final portfolio JSON now with no further tool calls.",
            })

        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=4096,
            tools=TOOLS,
            messages=messages,
        )
        api_counter["calls"] += 1
        calls_used += 1

        choice = response.choices[0]
        print(f"  [iter {iteration+1}] finish_reason={choice.finish_reason}")

        if choice.finish_reason == "tool_calls":

            if api_counter["calls"] >= DAILY_API_CAP:
                messages.append({"role": "assistant", "content": choice.message.content or ""})
                messages.append({
                    "role": "user",
                    "content": "No more tool calls allowed. Output your JSON portfolio now.",
                })
                continue

            messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)

                print(f"    -> {fn_name}({json.dumps(fn_args)})")
                result = TOOL_FUNCTIONS[fn_name](**fn_args)
                result_json = json.dumps(result)
                print(f"    <- {result_json[:90]}...")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_json,
                })

        elif choice.finish_reason == "stop":
            final_text = choice.message.content or ""
            parsed = _parse_json(final_text)
            if parsed is not None:
                return parsed, calls_used
            return {"raw_response": final_text}, calls_used

        else:
            break

    return {"error": "Loop ended without a final answer"}, calls_used


def _parse_json(text: str) -> dict | None:
    """Try to extract a JSON object from model output, handling markdown fences."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    fence_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass
    return None
