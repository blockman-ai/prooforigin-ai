import pandas as pd
from sklearn.model_selection import train_test_split
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam

# Load metadata
df = pd.read_csv("data/metadata/labels.csv")

# Convert labels
df["binary_label"] = df["label"].apply(lambda x: 1 if x == "ai_generated" else 0)

# Paths
def build_path(row):
    if row["label"] == "ai_generated":
        return "data/raw/ai_generated/" + row["filename"]
    else:
        return "data/raw/real/" + row["filename"]

df["filepath"] = df.apply(build_path, axis=1)

# Train/test split
train_df, val_df = train_test_split(
    df,
    test_size=0.2,
    random_state=42
)

# Image generators
train_datagen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=10,
    zoom_range=0.1,
    horizontal_flip=True
)

val_datagen = ImageDataGenerator(rescale=1./255)

train_generator = train_datagen.flow_from_dataframe(
    train_df,
    x_col="filepath",
    y_col="label",
    target_size=(224, 224),
    batch_size=8,
    class_mode="binary"
)

val_generator = val_datagen.flow_from_dataframe(
    val_df,
    x_col="filepath",
    y_col="label",
    target_size=(224, 224),
    batch_size=8,
    class_mode="binary"
)

# Base model
base_model = MobileNetV2(
    weights="imagenet",
    include_top=False,
    input_shape=(224, 224, 3)
)

x = base_model.output
x = GlobalAveragePooling2D()(x)
x = Dense(128, activation="relu")(x)
predictions = Dense(1, activation="sigmoid")(x)

model = Model(inputs=base_model.input, outputs=predictions)

# Freeze base model
for layer in base_model.layers:
    layer.trainable = False

model.compile(
    optimizer=Adam(learning_rate=0.001),
    loss="binary_crossentropy",
    metrics=["accuracy"]
)

# Train
model.fit(
    train_generator,
    validation_data=val_generator,
    epochs=5
)

# Save model
model.save("prooforigin_model.h5")

print("Training complete.")
