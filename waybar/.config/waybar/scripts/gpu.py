"""Read-only NVIDIA utilization; degrade gracefully if the GPU is unavailable."""
import json
import subprocess

try:
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=3, check=True,
    )
    usage, temperature = (int(value.strip()) for value in result.stdout.splitlines()[0].split(","))
    output = {"text": f"GPU {usage}%", "tooltip": f"NVIDIA GPU: {usage}% utilization, {temperature}°C"}
except (OSError, subprocess.SubprocessError, ValueError, IndexError):
    output = {"text": "GPU --", "tooltip": "NVIDIA metrics unavailable"}
print(json.dumps(output))
