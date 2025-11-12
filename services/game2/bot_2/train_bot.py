# services/game2/bot/train_bot.py
import torch
from torch.utils.data import DataLoader, random_split
import torch.nn.functional as F
import torch.optim as optim
import matplotlib.pyplot as plt
from bot_gru_model import GRUPolicy
from dataset import BotDataset

# DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"🚀 Using device: {DEVICE}")
if DEVICE.type == "cuda":
    print(f"GPU name: {torch.cuda.get_device_name(0)}")
    print(f"Memory Allocated: {torch.cuda.memory_allocated(0)/1024**2:.1f} MB")
    print(f"Memory Cached: {torch.cuda.memory_reserved(0)/1024**2:.1f} MB")

def train_bot(
    data_path="data/actions.jsonl",
    epochs=10,
    batch_size=64,
    lr=1e-3,
    save_path="gru_policy.pt",
    val_split=0.2
):
    # --- Load dataset and split to train/val ---
    dataset = BotDataset(data_path)
    n_total = len(dataset)
    n_val = int(val_split * n_total)
    n_train = n_total - n_val
    train_ds, val_ds = random_split(dataset, [n_train, n_val])

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    # --- Init model ---
    model = GRUPolicy().to(DEVICE)
    optimizer = optim.Adam(model.parameters(), lr=lr)

    train_losses, val_losses = [], []
    train_accs, val_accs = [], []

    for epoch in range(epochs):
        model.train()
        total_loss, correct, total = 0, 0, 0

        for rows, cols, states, actions, targets in train_loader:
            rows, cols, states, actions, targets = (
                rows.to(DEVICE),
                cols.to(DEVICE),
                states.to(DEVICE),
                actions.to(DEVICE),
                targets.to(DEVICE),
            )

            logits = model(rows, cols, states, actions)
            loss = F.cross_entropy(logits, targets - 1)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            pred = torch.argmax(logits, dim=1) + 1
            correct += (pred == targets).sum().item()
            total += targets.size(0)

        train_loss = total_loss / len(train_loader)
        train_acc = correct / total

        # --- Validation ---
        model.eval()
        val_loss, val_correct, val_total = 0, 0, 0
        with torch.no_grad():
            for rows, cols, states, actions, targets in val_loader:
                rows, cols, states, actions, targets = (
                    rows.to(DEVICE),
                    cols.to(DEVICE),
                    states.to(DEVICE),
                    actions.to(DEVICE),
                    targets.to(DEVICE),
                )

                logits = model(rows, cols, states, actions)
                loss = F.cross_entropy(logits, targets - 1)
                val_loss += loss.item()
                pred = torch.argmax(logits, dim=1) + 1
                val_correct += (pred == targets).sum().item()
                val_total += targets.size(0)

        val_loss /= len(val_loader)
        val_acc = val_correct / val_total

        train_losses.append(train_loss)
        val_losses.append(val_loss)
        train_accs.append(train_acc)
        val_accs.append(val_acc)

        print(f"Epoch {epoch+1}/{epochs} | "
              f"Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f} | "
              f"Train Acc: {train_acc:.3f}, Val Acc: {val_acc:.3f}")

    # --- Save model ---
    torch.save(model.state_dict(), save_path)
    print(f"\n✅ Model saved: {save_path}")

    # --- Plot graphs ---
    plt.figure(figsize=(10,4))
    plt.subplot(1,2,1)
    plt.plot(train_losses, label="Train Loss")
    plt.plot(val_losses, label="Val Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.title("Loss over epochs")
    plt.legend()

    plt.subplot(1,2,2)
    plt.plot(train_accs, label="Train Accuracy")
    plt.plot(val_accs, label="Val Accuracy")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.title("Accuracy over epochs")
    plt.legend()

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    try:
        train_bot()
    except Exception as e:
        import traceback;traceback.print_exc()
