# Genie LLM Bundle: Llama-3.2-3B-Instruct for Snapdragon X Elite

This bundle contains configuration and assets for deploying **Llama-3.2-3B-Chat-Quantized** on the **Qualcomm Hexagon Tensor Processor (HTP)** via the **Genie SDK (Generative AI Inference Extensions)**.

## Directory Layout

```
models/genie_bundle/
├── genie-config.json                         # Primary Genie runtime configuration
├── htp_backend_ext_config.json               # Hexagon HTP v73 accelerator config
├── tokenizer.json                            # BPE Tokenizer from Hugging Face
├── llama_v3_2_3b_instruct_part_1_of_3.bin    # QNN Context Binary (Layers 0-9)
├── llama_v3_2_3b_instruct_part_2_of_3.bin    # QNN Context Binary (Layers 10-19)
└── llama_v3_2_3b_instruct_part_3_of_3.bin    # QNN Context Binary (Layers 20-27 + Head)
```

## Compilation / Export via Qualcomm AI Hub

To export the quantized binary assets from source:

```powershell
# 1. Login to Hugging Face with access to meta-llama/Llama-3.2-3B-Instruct
hf auth login

# 2. Export Genie context binaries targeting Snapdragon X Elite CRD
python scripts/export_llama_genie.py `
  --device "Snapdragon X Elite CRD" `
  --output-dir models/genie_bundle
```

## Running on Target Hardware (HP OmniBook X)

```powershell
# In PowerShell on Snapdragon X Windows 11 ARM64:
$env:QAIRT_HOME = "C:\Program Files\Qualcomm\QAIRT"
$env:Path = "$env:QAIRT_HOME\bin\aarch64-windows-msvc;" + $env:Path
$env:ADSP_LIBRARY_PATH = "$env:QAIRT_HOME\lib\hexagon-v73\unsigned"

# Execute inference via Genie CLI:
genie-t2t-run -c models/genie_bundle/genie-config.json -p "Rewrite this document in plain language..."
```
