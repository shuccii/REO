import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

df = pd.read_csv("conductivity.csv")
df = df.iloc[::2]
fig, ax = plt.subplots()
ax.plot(df["T"], df["sigma"], "o-", color="tab:blue", label="measured")
ax.set_xlabel("Temperature [K]")
ax.set_ylabel("Conductivity [S/m]")
ax.legend(loc="lower right")
fig.savefig("plot.png", dpi=150)
