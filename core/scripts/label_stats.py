import pandas as pd

df = pd.read_csv("data/metadata/dataset.csv")
print(df["final_label"].value_counts())
