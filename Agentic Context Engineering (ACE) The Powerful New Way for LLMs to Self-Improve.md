---
title: "Agentic Context Engineering (ACE): The Powerful New Way for LLMs to Self-Improve"
source: "https://medium.com/coding-nexus/agentic-context-engineering-ace-the-powerful-new-way-for-llms-to-self-improve-93b9559432a2"
author:
  - "[[Code Coup]]"
published: 2025-12-08
created: 2025-12-13
description: "Agentic Context Engineering (ACE): The Powerful New Way for LLMs to Self-Improve Large language models are remarkable — but they’re also costly, slow to update, and require complex fine-tuning …"
tags:
  - "clippings"
---
[Sitemap](https://medium.com/sitemap/sitemap.xml)## [Coding Nexus](https://medium.com/coding-nexus?source=post_page---publication_nav-16e3527896e0-93b9559432a2---------------------------------------)

[![Coding Nexus](https://miro.medium.com/v2/resize:fill:76:76/1*KCZtO6-wFqmTaMmbTMicbw.png)](https://medium.com/coding-nexus?source=post_page---post_publication_sidebar-16e3527896e0-93b9559432a2---------------------------------------)

Coding Nexus is a community of developers, tech enthusiasts, and aspiring coders. Whether you’re exploring the depths of Python, diving into data science, mastering web development, or staying updated on the latest trends in AI, Coding Nexus has something for you.

Large language models are remarkable — but they’re also costly, slow to update, and require complex fine-tuning processes.

What if models could **self-improve continuously**, simply by evolving their *context rather* than their *weights*?

That’s exactly what **Agentic Context Engineering (ACE)** delivers.

ACE is a new framework that regards the model’s context as a living, evolving playbook — one that gets better over time through generation, reflection, and strategic curation.

And the results are astonishing:

- **+10.6%** improvement on agent tasks
- **+8.6%** improvement on financial reasoning
- **−86.9% latency** and **−83.6% dollar cost**
- Works with **any LLM** (open or closed source)
- Produces **human-readable learning** and supports selective unlearning

This is **self-supervised learning for LLMs**, without touching the weights.

In this article, I’ll explain ACE in simple terms — with examples and code — so you can understand how it works and how to use it today.

![](https://miro.medium.com/v2/resize:fit:640/format:webp/1*Jw74msispClhk3Q3uL3bqg.png)

## What Problem Does ACE Solve?

Current LLM adaptation methods often depend on:

- **Fine-tuning**, which is expensive and slow
- **Long system prompts**, which collapse over time
- **Ad-hoc memory**, which becomes noisy or redundant

ACE addresses all three problems by establishing a structured, evolving context — a playbook — that becomes smarter each time the model makes a mistake or identifies a new pattern.

Think of it like Git, but for LLM reasoning.

Instead of rewriting prompts, ACE uses **delta updates** — small, targeted edits — based on what the agent learns.

## How ACE Works

ACE runs using **three agent roles**, each with a specific job:

## 1\. Generator

Handles the task, develops reasoning paths, outputs mistakes and successes.

## 2\. Reflector

Reads those trajectories and extracts:

- useful strategies
- patterns
- pitfalls
- mistakes to avoid

## 3\. Curator

Updates the playbook using:

- de-duplication
- pruning
- merging
- helpful/harmful counters

This ensures the playbook grows steadily and never collapses into noise.

## What the Playbook Looks Like

A playbook is just a structured text file that evolves:

```rb
## STRATEGIES & INSIGHTS
[str-00001] helpful=5 harmful=0 :: Always verify data types before processing.
[str-00002] helpful=3 harmful=1 :: Consider edge cases in financial data.

## FORMULAS & CALCULATIONS
[cal-00003] helpful=8 harmful=0 :: NPV = Σ(Cash Flow / (1+r)^t)
## COMMON MISTAKES TO AVOID
[mis-00004] helpful=6 harmful=0 :: Don't forget timezone conversions.
```

Each bullet has:

```rb
| Field               | Meaning                                  |
| ------------------- | ---------------------------------------- |
| ID                  | Stable reference                         |
| helpful/harmful     | Counts updated over time                 |
| Content             | The actual strategy, insight, or formula |
```

This makes the “model’s learning” **auditable, editable, and interpretable.**

## Why ACE Is a Breakthrough

## No fine-tuning needed

ACE adapts models using *only prompts* and *context evolution*.

## Extremely efficient

Compared to strong baselines:

- **−82.3% latency** (offline)
- **−91.5% latency** (online)
- **−83.6% token cost**

## High performance

Outperforms GPT-4.1 on difficult test splits in AppWorld using a smaller open-source model.

## Works everywhere

OpenAI, Together, SambaNova, DeepSeek, local LLMs — ACE is model-agnostic.

## Easy to extend

You only need three functions to plug in new domains.

## Installing and Using ACE

## 1\. Clone the repo

```rb
git clone https://github.com/ace-agent/ace.git
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env
```

## Basic ACE Setup in Python

```rb
from ace import ACE
from utils import initialize_clients

api_provider = "sambanova"  # or openai / together
ace_system = ACE(
    api_provider=api_provider,
    generator_model="DeepSeek-V3.1",
    reflector_model="DeepSeek-V3.1",
    curator_model="DeepSeek-V3.1",
    max_tokens=4096
)
config = {
    'num_epochs': 1,
    'max_num_rounds': 3,
    'curator_frequency': 1,
    'eval_steps': 100,
    'online_eval_frequency': 15,
    'save_steps': 50,
    'playbook_token_budget': 80000,
    'task_name': 'your_task',
    'json_mode': False,
    'no_ground_truth': False,
    'save_dir': './results',
    'test_workers': 20,
    'use_bulletpoint_analyzer': False,
    'api_provider': api_provider
}
```

## Offline Adaptation

```rb
results = ace_system.run(
    mode='offline',
    train_samples=train_data,
    val_samples=val_data,
    test_samples=test_data,
    data_processor=processor,
    config=config
)
```

## Online Adaptation

```rb
results = ace_system.run(
    mode='online',
    test_samples=test_data,
    data_processor=processor,
    config=config
)
```

## Evaluation Only

```rb
results = ace_system.run(
    mode='eval_only',
    test_samples=test_data,
    data_processor=processor,
    config=config
)
```

## Finance Example: FiNER / XBRL Formula

ACE includes a ready-made runner:

```rb
python -m finance.run \
    --task_name finer \
    --mode offline \
    --save_path results
```

Or online:

```rb
python -m finance.run \
    --task_name finer \
    --mode online \
    --save_path results
```

Or evaluation only:

```rb
python -m finance.run \
    --task_name finer \
    --mode eval_only \
    --initial_playbook_path results/.../best_playbook.txt \
    --save_path test_results
```

## Extending ACE to Your Own Domain

You only need to implement a lightweight `DataProcessor`.

## Minimal Example

```rb
class DataProcessor:
    def process_task_data(self, raw_data):
        return [{
            "context": item["ctx"],
            "question": item["q"],
            "target": item["answer"],
            "others": {}
        }]

def answer_is_correct(self, predicted, ground_truth):
        return predicted.strip() == ground_truth.strip()
    def evaluate_accuracy(self, preds, truths):
        correct = sum(self.answer_is_correct(p, t) for p, t in zip(preds, truths))
        return correct / len(preds)
```

Once this is done, ACE handles:

- parallelized evaluation
- curated updates
- playbook evolution
- logging
- checkpointing
- curation diffs

Everything else is automatic.

## ACE Is the Future of Model Adaptation

ACE shows a new path forward:  
**models improving themselves by evolving their context, not retraining their weights.**

This is:

- cheaper
- faster
- more interpretable
- easier to control
- easier to deploy

As LLMs evolve from basic chatbots to fully autonomous systems, frameworks like ACE will become essential.

If weight-free learning becomes standard — ACE will have been one of the first significant steps.

[![Coding Nexus](https://miro.medium.com/v2/resize:fill:96:96/1*KCZtO6-wFqmTaMmbTMicbw.png)](https://medium.com/coding-nexus?source=post_page---post_publication_info--93b9559432a2---------------------------------------)

[![Coding Nexus](https://miro.medium.com/v2/resize:fill:128:128/1*KCZtO6-wFqmTaMmbTMicbw.png)](https://medium.com/coding-nexus?source=post_page---post_publication_info--93b9559432a2---------------------------------------)

[Last published 1 hour ago](https://medium.com/coding-nexus/historic-financial-ratios-for-your-hedge-fund-in-arcticdb-77d10e572ffc?source=post_page---post_publication_info--93b9559432a2---------------------------------------)

Coding Nexus is a community of developers, tech enthusiasts, and aspiring coders. Whether you’re exploring the depths of Python, diving into data science, mastering web development, or staying updated on the latest trends in AI, Coding Nexus has something for you.

Code Coup: Seize the Code, Stage a Coup!

## More from the list: "Development "

Curated by[Terry Yodaiken](https://medium.com/@poviewai?source=post_page---list_recirc--93b9559432a2-----------5eb432556589----------------------------)## [Top 10+ Open Source No-Code AI Tools with the Most GitHub Stars](https://medium.com/lets-code-future/top-10-open-source-no-code-ai-tools-with-the-most-github-stars-ef39a71cfddd?source=post_page---list_recirc--93b9559432a2-----------5eb432556589----------------------------)

3d ago[Jannis](https://medium.com/@PowerUpSkills?source=post_page---list_recirc--93b9559432a2-----------5eb432556589----------------------------)## [RAG on Everything: Lets Build a Private AI Engine With 97 Percent Less Storage](https://medium.com/@PowerUpSkills/rag-on-everything-lets-build-a-private-ai-engine-with-97-percent-less-storage-d83e41039a2b?source=post_page---list_recirc--93b9559432a2-----------5eb432556589----------------------------)

Dec 5[Reza Rezvani](https://medium.com/@alirezarezvani?source=post_page---list_recirc--93b9559432a2-----------5eb432556589----------------------------)## [Stop Teaching Claude the Same Thing Every Day: Build Your Persistent AI Development Team](https://medium.com/@alirezarezvani/stop-teaching-claude-the-same-thing-every-day-build-your-persistent-ai-development-team-e41b416e3e19?source=post_page---list_recirc--93b9559432a2-----------5eb432556589----------------------------)

Nov 24[Somendradev](https://medium.com/@somendradev23?source=post_page---list_recirc--93b9559432a2-----------5eb432556589----------------------------)## [15 Small Dev Tools That Quietly Do the Work of Big Expensive Software](https://medium.com/@somendradev23/15-small-dev-tools-that-quietly-do-the-work-of-big-expensive-software-c31592062b70?source=post_page---list_recirc--93b9559432a2-----------5eb432556589----------------------------)

Dec 5## [ToolOrchestra: The Tiny 8B Model From NVIDIA That Shows Us the Future of AI Agents](https://medium.com/coding-nexus/toolorchestra-the-tiny-8b-model-from-nvidia-that-shows-us-the-future-of-ai-agents-91678f367a74?source=post_page---list_recirc--93b9559432a2-----------5eb432556589----------------------------)

Dec 2## [Appwrite Sites: The Open-Source Vercel Alternative Developers Have Been Waiting For](https://medium.com/coding-nexus/appwrite-sites-the-open-source-vercel-alternative-developers-have-been-waiting-for-e721f3e6432f?source=post_page---list_recirc--93b9559432a2-----------5eb432556589----------------------------)

Dec 2

In[Stackademic](https://medium.com/stackademic?source=post_page---list_recirc--93b9559432a2-----------5eb432556589----------------------------)

by[Somendradev](https://medium.com/@somendradev23?source=post_page---list_recirc--93b9559432a2-----------5eb432556589----------------------------)## [12 Niche Developer Tools You Didn’t Know Existed](https://medium.com/stackademic/12-niche-developer-tools-you-didnt-know-existed-b726bd495d9a?source=post_page---list_recirc--93b9559432a2-----------5eb432556589----------------------------)

Nov 28

In[UX Planet](https://medium.com/ux-planet?source=post_page---list_recirc--93b9559432a2-----------5eb432556589----------------------------)

by[Sergushkin.com](https://medium.com/@sergushkin?source=post_page---list_recirc--93b9559432a2-----------5eb432556589----------------------------)## [New UX/UI + AI Design Tools You Need to Try!](https://medium.com/ux-planet/new-ux-ui-ai-design-tools-you-need-to-try-8fdcdbe93073?source=post_page---list_recirc--93b9559432a2-----------5eb432556589----------------------------)

Nov 30[TheMindShift](https://medium.com/@themindshift?source=post_page---list_recirc--93b9559432a2-----------5eb432556589----------------------------)## [Top 8 Tool Tech Stacks That Make Building a RAG System Really Easy](https://medium.com/@themindshift/top-8-tool-tech-stacks-that-make-building-a-rag-system-really-easy-03642b5c57bd?source=post_page---list_recirc--93b9559432a2-----------5eb432556589----------------------------)

Nov 5## [Google’s new T5Gemma is smart and designed for you — part 2](https://medium.com/artificial-intel-ligence-playground/googles-new-t5gemma-is-smart-and-designed-for-you-part-2-7dad9c990c2b?source=post_page---list_recirc--93b9559432a2-----------5eb432556589----------------------------)

Nov 13

[View list](https://blog.poview.ai/list/development-5eb432556589?source=post_page---list_recirc--93b9559432a2-----------5eb432556589----------------------------)

## More from Code Coup and Coding Nexus

## Recommended from Medium

[

See more recommendations

](https://medium.com/?source=post_page---read_next_recirc--93b9559432a2---------------------------------------)