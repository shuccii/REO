import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

df = pd.read_csv("conductivity.csv")
fig, ax = plt.subplots()
ax.plot(df["T"], df["sigma"], "o-", color="black", label="measured")
ax.set_xlabel("Temperature")
ax.set_ylabel("Conductivity")
ax.legend(loc="upper left")
fig.savefig("plot.png", dpi=150)
