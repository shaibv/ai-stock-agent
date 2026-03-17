from dotenv import load_dotenv
load_dotenv()

from datetime import date
from agent import run_agent
from prompts import MOMENTUM_PROMPT, VALUE_PROMPT
from tracker import load_state, save_state, execute_rebalance, calculate_value
from portfolio import display_portfolio, validate_portfolio, display_competition
from logger import write_daily_log


def run_daily():
    state = load_state()
    api_counter = {"calls": 0}
    today = date.today().isoformat()

    print(f"\n{'='*62}")
    print(f"  DAILY RUN — {today}")
    print(f"{'='*62}")

    daily_results = {}

    for name, prompt in [("momentum", MOMENTUM_PROMPT), ("value", VALUE_PROMPT)]:
        agent_state = state["agents"][name]
        prev_portfolio = agent_state.get("last_portfolio")
        prev_value = calculate_value(agent_state)

        label = "🔴 MOMENTUM TRADER" if name == "momentum" else "🔵 VALUE ANALYST"
        print(f"\n{'─'*62}")
        print(f"  Running {label}  (prev value: ${prev_value:,.0f})")
        print(f"{'─'*62}")

        portfolio, calls_used = run_agent(prompt, prev_portfolio, api_counter)
        print(f"  Agent used {calls_used} API calls (total today: {api_counter['calls']})")

        if not validate_portfolio(portfolio):
            print(f"  {name}: invalid portfolio, skipping rebalance")
            continue

        rebalance_info = execute_rebalance(agent_state, portfolio)
        display_portfolio(label, portfolio, rebalance_info)

        daily_results[name] = rebalance_info

        write_daily_log(
            agent_name=name,
            prev_value=rebalance_info["prev_value"],
            new_value=rebalance_info["new_value"],
            trades=rebalance_info["trades"],
            old_portfolio=rebalance_info["old_portfolio"],
            new_portfolio=portfolio,
            holdings=agent_state["holdings"],
            cash=agent_state["cash"],
        )
        print(f"  Log appended to data/{name}.log")

    save_state(state)
    display_competition(state, daily_results)
    print(f"  Total API calls today: {api_counter['calls']}")
    print(f"  State saved to data/history.json\n")


if __name__ == "__main__":
    run_daily()
