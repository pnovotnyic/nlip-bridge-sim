import os
import sys
import time
import csv
from pathlib import Path
from openai import OpenAI

# Root of the repository
ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "experiments"))

from nlipeval.backends.world import World
from nlipeval.backends.profile_table import render_profile_table
from nlipeval.models.smoke import _filler

def run_test(num_parallel: int) -> list[dict]:
    print(f"\n========================================================")
    print(f"Starting Ollama with OLLAMA_NUM_PARALLEL={num_parallel}...")
    print(f"========================================================")
    # Start the server using the shell script
    os.system(f"OLLAMA_NUM_PARALLEL={num_parallel} {ROOT}/scripts/start_ollama_r1.sh OLLAMA_NUM_PARALLEL={num_parallel}")
    
    # Initialize OpenAI client (Ollama OpenAI compatibility endpoint)
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    
    # Load specifications from excerpts_prompt
    client_spec_path = ROOT / "experiments" / "specs" / "excerpts_prompt" / "L3" / "v0.8.1.json"
    server_spec_path = ROOT / "experiments" / "specs" / "excerpts_prompt" / "L3" / "v1.1.0.json"
    
    client_spec = client_spec_path.read_text()
    server_spec = server_spec_path.read_text()
    
    world = World()
    profiles = render_profile_table(world)
    
    client_prefix = "You are a telecom client assisting an API integration. Here is the specification of the L3 API v0.8.1:\n\n" + client_spec
    server_prefix = "You are a telecom operator server assistant. Here is the specification of the L3 API v1.1.0:\n\n" + server_spec + "\n\nHere are the QoS profiles available on the server:\n\n" + profiles
    
    rounds_data = []
    print("Running 10 rounds of alternating calls (concurrency=1)...")
    for round_idx in range(1, 11):
        # Client call
        client_prompt = client_prefix + f"\n\nUser request details:\n{_filler(150, round_idx)}\n\nGenerate the client request payload."
        t0 = time.monotonic()
        client.chat.completions.create(
            model="nlip-qwen3-4b",
            messages=[{"role": "user", "content": client_prompt}],
            max_tokens=300,
            temperature=0.6,
            seed=0
        )
        t_client = time.monotonic() - t0
        
        # Server call
        server_prompt = server_prefix + f"\n\nServer state details:\n{_filler(150, round_idx + 10)}\n\nGenerate the server response payload."
        t0 = time.monotonic()
        client.chat.completions.create(
            model="nlip-qwen3-4b",
            messages=[{"role": "user", "content": server_prompt}],
            max_tokens=300,
            temperature=0.6,
            seed=0
        )
        t_server = time.monotonic() - t0
        
        print(f"Round {round_idx}: client={t_client:.2f}s, server={t_server:.2f}s")
        rounds_data.append({
            "round": round_idx,
            "client_s": t_client,
            "server_s": t_server
        })
        
    return rounds_data

def main():
    # 1. Run with OLLAMA_NUM_PARALLEL=1
    rounds_1 = run_test(1)
    
    # 2. Run with OLLAMA_NUM_PARALLEL=2
    rounds_2 = run_test(2)
    
    # Write to results/stage01/r1_alternating.csv (discarding the first round of each)
    output_dir = ROOT / "experiments" / "results" / "stage01"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = output_dir / "r1_alternating.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["num_parallel", "round", "side", "seconds"])
        # OLLAMA_NUM_PARALLEL=1
        for r in rounds_1[1:]:
            writer.writerow(["1", r["round"], "client", f"{r['client_s']:.4f}"])
            writer.writerow(["1", r["round"], "server", f"{r['server_s']:.4f}"])
        # OLLAMA_NUM_PARALLEL=2
        for r in rounds_2[1:]:
            writer.writerow(["2", r["round"], "client", f"{r['client_s']:.4f}"])
            writer.writerow(["2", r["round"], "server", f"{r['server_s']:.4f}"])
            
    print(f"\nSaved R1 alternating latency results to {csv_path}")

if __name__ == "__main__":
    main()
