import json, random, re, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import spacy

nlp = spacy.load("en_core_web_sm")

def damage_pos(text: str, ratio=0.4) -> dict:
    doc = nlp(text)
    candidates = [t for t in doc
                  if t.pos_ in {"NOUN", "VERB", "NUM", "PROPN"}
                  and not t.is_punct]
    if not candidates:
        return {"damaged": text, "removed": []}
    n      = max(1, int(len(candidates) * ratio))
    picked = {t.i for t in random.sample(candidates,
                                          min(n, len(candidates)))}
    damaged, removed = [], []
    for t in doc:
        if t.i in picked:
            damaged.append("___")
            removed.append({"word": t.text, "pos": t.pos_})
        else:
            damaged.append(t.text)
    return {"damaged": " ".join(damaged), "removed": removed}


def damage_truncate(text: str, ratio=0.6) -> dict:
    cut = int(len(text) * random.uniform(0.4, ratio))
    return {
        "damaged": text[:cut] + " [INCOMPLETE]",
        "removed": [text[cut:]]
    }


def damage_sentences(text: str) -> dict:
    sents = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sents) < 2:
        return {"damaged": text, "removed": []}
    idx        = random.randint(0, len(sents) - 1)
    removed    = sents[idx]
    sents[idx] = "[MISSING RULE]"
    return {"damaged": " ".join(sents), "removed": [removed]}


STRATEGIES = {
    "pos":       damage_pos,
    "truncate":  damage_truncate,
    "sentences": damage_sentences
}


def generate_dataset(json_path: str, output_path: str,
                     n_variants=3) -> list:
    """
    Lit games_index.json → génère des règles endommagées
    → sauvegarde eval_dataset.json
    """
    if not os.path.exists(json_path):
        print(f"ERROR: {json_path} not found")
        print("Run ludii_scraper.py first")
        sys.exit(1)

    with open(json_path, encoding="utf-8") as f:
        games = json.load(f)

    print(f"Generating damaged dataset from {len(games)} games...")
    dataset = []

    for game in games:
        rules = game.get("rules_text", "").strip()[:400]
        if len(rules) < 60:
            print(f"  Skipping {game['name']} (rules too short)")
            continue

        print(f"  Processing {game['name']}...")
        for strat_name, strat_fn in STRATEGIES.items():
            for v in range(n_variants):
                try:
                    res = strat_fn(rules)
                    dataset.append({
                        "id":       f"{game['name']}_{strat_name}_{v}",
                        "game":     game["name"],
                        "strategy": strat_name,
                        "variant":  v,
                        "original": rules,
                        "damaged":  res["damaged"],
                        "removed":  res["removed"]
                    })
                except Exception as e:
                    print(f"  Error {game['name']}/{strat_name}: {e}")

    # Sauvegarde
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    # Stats
    print(f"\nDataset generated: {len(dataset)} pairs")
    print(f"Saved to: {output_path}")
    print("\nDistribution by strategy:")
    by_strat = {}
    for item in dataset:
        s = item["strategy"]
        by_strat[s] = by_strat.get(s, 0) + 1
    for s, n in by_strat.items():
        print(f"  {s:12s}: {n} pairs")

    # Apercu d'un exemple par stratégie
    print("\nSample per strategy:")
    seen = set()
    for item in dataset:
        if item["strategy"] not in seen:
            seen.add(item["strategy"])
            print(f"\n  [{item['strategy'].upper()}] {item['game']}")
            print(f"  Original : {item['original'][:80]}...")
            print(f"  Damaged  : {item['damaged'][:80]}...")

    return dataset


if __name__ == "__main__":
    generate_dataset(
        json_path=(
            "./phase1_ludii_rag/datasets/raw_lud/games_index.json"
        ),
        output_path=(
            "./phase1_ludii_rag/datasets/eval_dataset.json"
        ),
        n_variants=3
    )