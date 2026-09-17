#!/usr/bin/env python3
"""意图识别模型微调脚本（适合 6G 显存）"""

import json
from pathlib import Path

def prepare_training_data():
    """准备训练数据"""
    dataset_path = Path("data/training/intent_dataset.json")
    if not dataset_path.exists():
        print("数据集不存在，请先创建")
        return
    
    with open(dataset_path) as f:
        data = json.load(f)
    
    training_data = []
    for intent in data['intents']:
        for example in intent['examples']:
            training_data.append({
                "input": example,
                "output": intent['name']
            })
    
    print(f"准备训练数据: {len(training_data)} 条")
    print(f"意图类别: {[i['name'] for i in data['intents']]}")
    
    # 保存为训练格式
    output_path = Path("data/training/training_data.json")
    with open(output_path, 'w') as f:
        json.dump(training_data, f, indent=2)
    print(f"✅ 训练数据已保存: {output_path}")
    
    return training_data

def finetune_with_ollama():
    """使用 Ollama 进行微调"""
    print("\n使用 Ollama 微调（需要先安装 llama.cpp 或使用 LoRA）")
    print("推荐方案:")
    print("1. 使用 unsloth 进行 QLoRA 微调（适合 6G 显存）")
    print("2. 使用 Ollama 的 Modelfile 自定义提示词")
    
    # 生成 Modelfile
    modelfile = f'''FROM qwen2.5:7b-instruct-q4_0-gpu

SYSTEM 你是一个意图识别助手。分析用户输入，返回以下意图之一：
code, weather, translate, calculate, greeting, farewell, thanks, memory, analysis

只返回意图名称，不要有其他内容。

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_predict 32
'''
    
    with open("Modelfile.intent", "w") as f:
        f.write(modelfile)
    print("\n✅ 已生成 Modelfile.intent")
    print("运行以下命令创建自定义模型:")
    print("  ollama create intent-model -f Modelfile.intent")

if __name__ == "__main__":
    prepare_training_data()
    finetune_with_ollama()
