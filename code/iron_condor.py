import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button

def option_payoff(price, leg):
    """Calculate payoff for a single option leg at expiry."""
    option_type = leg["type"].lower()
    position = leg["position"].lower()
    strike = leg["strike"]
    premium = leg["premium"]

    payoff = 0
    if option_type == "call":
        payoff = max(0, price - strike)
    elif option_type == "put":
        payoff = max(0, strike - price)

    # Long pays premium, short receives premium
    if position == "long":
        return payoff - premium
    elif position == "short":
        return -(payoff - premium)
    else:
        raise ValueError("Position must be 'long' or 'short'")


def portfolio_payoff(legs, price_range, lot_size=100):
    """Calculate total payoff for all legs across price range."""
    total_payoffs = []
    for price in price_range:
        total = sum(option_payoff(price, leg) for leg in legs)
        total_payoffs.append(total * lot_size)
    return np.array(total_payoffs)


def analyze_strategy(legs, spot_price, lot_size=100):
    """Compute max profit, max loss, and breakeven points."""
    # Adaptive step size: 0.5% of spot price, at least 1
    step = max(1, int(spot_price * 0.005))
    price_range = np.arange(int(spot_price * 0.5), int(spot_price * 1.5) + step, step)

    payoffs = portfolio_payoff(legs, price_range, lot_size)

    max_profit = np.max(payoffs)
    max_loss = np.min(payoffs)

    breakevens = []
    for i in range(1, len(price_range)):
        if payoffs[i-1] * payoffs[i] < 0:  # crosses zero
            breakevens.append(round(price_range[i], 2))

    # Current profit/loss at spot price
    current_pl = portfolio_payoff(legs, [spot_price], lot_size)[0]

    return {
        "Max Profit (per lot)": round(max_profit, 2),
        "Max Loss (per lot)": round(max_loss, 2),
        "Breakeven Points": breakevens,
        "Current P/L (per lot)": round(current_pl, 2),
        "Legs": legs,
        "Lot Size": lot_size,
        "Spot Price": spot_price
    }, price_range, payoffs


def plot_strategy(price_range, payoffs, breakevens, current_pl, legs, lot_size, spot_price):
    fig, ax = plt.subplots(figsize=(10,6))
    plt.subplots_adjust(bottom=0.25)  # space for buttons

    line, = ax.plot(price_range, payoffs, label="Strategy P/L")
    ax.axhline(0, color="black", linewidth=1)
    for b in breakevens:
        ax.axvline(b, linestyle="--", color="red", label=f"Breakeven {b}")

    # Initial zoom limited to ±10% around spot price
    x_min = spot_price * 0.9
    x_max = spot_price * 1.1
    mask = (price_range >= x_min) & (price_range <= x_max)
    y_min = payoffs[mask].min() * 1.1
    y_max = payoffs[mask].max() * 1.1

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)

    initial_xlim = (x_min, x_max)
    initial_ylim = (y_min, y_max)

    # Label current profit/loss outside the graph
    ax.text(price_range[-1], current_pl, f"Current P/L: {current_pl}",
             ha="right", va="bottom", fontsize=10, color="blue",
             bbox=dict(facecolor="white", edgecolor="blue", boxstyle="round,pad=0.3"))

    ax.set_title("Options Strategy Payoff Diagram")
    ax.set_xlabel("Underlying Price at Expiry")
    ax.set_ylabel("Profit / Loss (per lot)")
    ax.legend()
    ax.grid(True)

    # Crosshair lines, dot marker, and annotation
    hline = ax.axhline(color="gray", linestyle="--", linewidth=0.8)
    vline = ax.axvline(color="gray", linestyle="--", linewidth=0.8)
    dot, = ax.plot([], [], 'ro')  # red dot marker
    annotation = ax.annotate("", xy=(0,0), xytext=(10,10), textcoords="offset points",
                             bbox=dict(boxstyle="round", fc="w"))
    annotation.set_visible(False)

    def on_mouse_move(event):
        if not event.inaxes:
            return
        x = event.xdata
        if x is None:
            return
        # Interpolate P/L at projected price
        pl = float(np.interp(x, price_range, payoffs))

        # Update crosshairs
        hline.set_ydata([pl, pl])
        vline.set_xdata([x, x])

        # Update dot marker
        dot.set_data([x], [pl])

        # Update annotation
        annotation.xy = (x, pl)
        annotation.set_text(f"Price: {x:.2f}\nP/L: {pl:.2f}")
        annotation.set_visible(True)

        fig.canvas.draw_idle()

    fig.canvas.mpl_connect('motion_notify_event', on_mouse_move)

    # Add buttons
    ax_button_zoom = plt.axes([0.75, 0.05, 0.1, 0.075])
    button_zoom = Button(ax_button_zoom, 'Zoom Out')

    ax_button_reset = plt.axes([0.6, 0.05, 0.1, 0.075])
    button_reset = Button(ax_button_reset, 'Reset Zoom')

    def zoom_out(event):
        x_min, x_max = ax.get_xlim()
        y_min, y_max = ax.get_ylim()
        x_range = (x_max - x_min)
        y_range = (y_max - y_min)
        ax.set_xlim(x_min - 0.2 * x_range, x_max + 0.2 * x_range)
        ax.set_ylim(y_min - 0.2 * y_range, y_max + 0.2 * y_range)
        fig.canvas.draw_idle()

    def reset_zoom(event):
        ax.set_xlim(initial_xlim)
        ax.set_ylim(initial_ylim)
        fig.canvas.draw_idle()

    button_zoom.on_clicked(zoom_out)
    button_reset.on_clicked(reset_zoom)

    plt.show()


# Example: Iron Condor in Indian market
if __name__ == "__main__":
    spot_price = 25000  # underlying price
    lot_size = 15       # example lot size for BANKNIFTY

    legs = [
        {"type": "put", "position": "short", "strike": 24500, "premium": 200},
        {"type": "put", "position": "long", "strike": 24000, "premium": 100},
        {"type": "call", "position": "short", "strike": 25500, "premium": 220},
        {"type": "call", "position": "long", "strike": 26000, "premium": 120},
    ]

    result, prices, payoffs = analyze_strategy(legs, spot_price, lot_size)
    for k, v in result.items():
        if k not in ["Legs", "Lot Size", "Spot Price"]:
            print(f"{k}: {v}")

    plot_strategy(prices, payoffs, result["Breakeven Points"], result["Current P/L (per lot)"],
                  result["Legs"], result["Lot Size"], result["Spot Price"])
