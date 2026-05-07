# make-task-AI

## 📝 プロジェクト概要 (Description)
AIエージェント（マルチエージェント）を活用し、曖昧なユーザーストーリーから具体的な開発タスクを自動生成・要件定義の壁打ちを行うシステムです。

## ✨ 主な機能 (Features)
- **ユーザーストーリーの洗練**: ユーザーのアイデアや要件をAIエージェントがヒアリング・深掘りし、明確な仕様に落とし込みます。
- **タスクの自動分解**: 洗練された要件をもとに、実装に必要な具体的なタスク（フロントエンド・バックエンド等）を自動で分割・生成します。
- **マルチエージェント・ワークフロー**: LangGraphを用いて、複数の専門エージェントによる協調作業を定義・実行しています。

## 🛠 技術スタック (Tech Stack)
- **言語**: Python
- **AI/LLM**: LangChain / LangGraph, OpenAI API
- **その他**: (例: 実行環境や使用しているライブラリなど)

## 🚀 環境構築 (Installation & Setup)
ローカル環境で動かすための手順を記載します。
```bash
# リポジトリのクローン
git clone [https://github.com/KaichoHarry/make-task-AI.git](https://github.com/KaichoHarry/make-task-AI.git)
cd make-task-AI

# 依存関係のインストール
pip install -r requirements.txt # または poetry / pipenv など

# 環境変数の設定
cp .env.example .env
# .envファイル内に必要なAPIキーなどを記述してください。