# Opponent Model Metrics

The **Opponent Model** section displays three key metrics that measure how well your strategy predicts the opponent's behavior.

## Entropy

**What it measures**: How uncertain your model is about the opponent's moves.

- **Range**: 0 to 4.91 bits (for 30 possible moves)
- **Lower is better**: Low entropy = confident predictions, high entropy = confused guesses
- **When recorded**: Snapshot at the start of each game, showing your model's baseline uncertainty

Think of entropy like a prediction roulette wheel—it measures how spread out your "chips" are. Concentrated chips = low entropy (confident). Spread everywhere = high entropy (uncertain).

### Examples

| Entropy | Meaning |
|---------|---------|
| 2.0-2.5 | Fairly confident (you've learned clear patterns) |
| 3.5-4.0 | Moderate uncertainty (still learning) |
| 4.5+ | Very confused (almost no information) |

---

## Top-3 Hit

**What it measures**: How often the opponent's actual move was in your top 3 predictions.

- **Range**: 0% to 100%
- **Higher is better**: 75% = "3 out of 4 times, the opponent did what I predicted might happen"
- **Per-move basis**: After each opponent move, the system checks: "was this move in my top 3 guesses?"
- **Aggregation**: Average of all those checks across the entire game

This is a practical "you got lucky" metric. Even if your model isn't assigning high probability to the move, if it was in your top 3 candidates, you caught it.

### Examples

| Top-3 Hit | Meaning |
|-----------|---------|
| 90%+ | Opponent is very predictable |
| 70-85% | Good predictability |
| 50-70% | Moderate predictability |
| <50% | Opponent surprises you often |

---

## Accuracy (Assigned Probability)

**What it measures**: How much probability your model assigned to the actual move the opponent made.

- **Range**: 0.0 to 1.0 (where 1.0 = 100%)
- **Higher is better**: 0.45 = "on average, I assigned 45% probability to moves opponent actually played"
- **Per-move basis**: You make a prediction distribution, then check "what probability did I give to the actual move?"
- **Aggregation**: Average across all opponent moves

This shows real **confidence** in your predictions. It's stricter than Top-3 Hit because your model needs to rank the actual move high and assign it significant probability, not just include it in the top 3.

### Examples

| Accuracy | Meaning |
|----------|---------|
| 0.50+ | Very confident in predictions |
| 0.35-0.50 | Good confidence |
| 0.20-0.35 | Moderate confidence |
| <0.20 | Low confidence (uncertain) |

---

## Interpreting Together

These three metrics tell complementary stories about your model:

### Scenario A: Entropy=2.0, Top-3=80%, Accuracy=0.35

**Diagnosis**: You know *what moves are possible*, but not *which one will happen*

- Your model is fairly sure about patterns (low entropy)
- Most opponent moves were predictable (high top-3)
- But you weren't assigning them high probability (low accuracy)
- **Implication**: Your model has learned some structure but lacks refinement

### Scenario B: Entropy=4.5, Top-3=45%, Accuracy=0.12

**Diagnosis**: Opponent is unpredictable or your model hasn't learned enough

- Your model has no idea what's happening (high entropy)
- The opponent surprised you often (low top-3)
- You were very uncertain about actual moves (low accuracy)
- **Implication**: Need more games to learn patterns, or opponent plays randomly

### Scenario C: Entropy=3.0, Top-3=90%, Accuracy=0.60

**Diagnosis**: Good model that understands opponent patterns

- Moderate uncertainty (learning in progress)
- Strong predictability of candidate moves
- High confidence in actual moves
- **Implication**: Model is working well despite some uncertainty

---

## How They're Calculated

### Data Collection During Game

1. **At game start**: Record model's baseline entropy (uncertainty level)
2. **After each opponent move**: Record what probability the model assigned to the move they actually played, and whether it was in the top 3 predictions
3. **At game end**: Aggregate all per-move metrics into averages

### Aggregation to Session View

The dashboard displays **session averages**—the mean of these metrics across all games in the current run. This gives you a sense of how your model is performing overall.

---

## Model Context

The opponent model uses a Bayesian approach with two information sources:

```
P(opponent_move) = 0.7 × P(move | your_last_move)
                 + 0.3 × P(move | game_phase)
```

This blended prediction is smoothed to avoid overconfidence and account for uncertainty in sparse data. Entropy, Top-3 Hit, and Accuracy all measure how well this model performs at runtime.
