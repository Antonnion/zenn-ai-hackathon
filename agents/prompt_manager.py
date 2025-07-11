"""プロンプト管理システムモジュール

このモジュールは、エージェントやワークフロー用のプロンプトを効率的に管理するための
機能を提供します。テンプレート継承、変数置換、メタデータ処理などの高度な機能を含みます。
従来のファイルベースのプロンプト読み込みと新しいフォーマットの両方をサポートします。
"""

import logging
import os
import re
from typing import Any, Dict

import yaml
from utils.logging import setup_cloud_logging
from agents.config import PROMPT_MAPPING
from utils.file_utils import read_prompt_file

logger = setup_cloud_logging("prompt_manager")


class PromptManager:
    """プロンプト管理クラス（シングルトン）"""

    _instance = None

    def __new__(cls, root_dir: str = None):
        """シングルトンパターン実装"""
        if cls._instance is None:
            cls._instance = super(PromptManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, root_dir: str = None):
        """
        プロンプトマネージャーを初期化（シングルトンではインスタンス時に一度だけ実行）

        Args:
            root_dir: プロンプトルートディレクトリ。省略時はデフォルト
        """
        if not self._initialized:
            self.root_dir = root_dir or os.path.join(
                os.path.dirname(__file__), "../prompts"
            )
            self.loaded_prompts = {}
            self.config = self._load_config()
            self._prompts_cache = {}
            self._initialized = True

    def _load_config(self) -> dict:
        """全体設定ファイルを読み込む"""
        config_path = os.path.join(self.root_dir, "config.yaml")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as file:
                    return yaml.safe_load(file)
            except Exception as e:
                logger.error(f"設定ファイルの読み込みに失敗: {e}")
                return {}
        return {}

    def get_prompt(self, prompt_key: str) -> str:
        """
        プロンプトキーからプロンプト内容を取得

        Args:
            prompt_key: プロンプトのキー

        Returns:
            プロンプト文字列

        Raises:
            ValueError: 指定されたキーが存在しない場合
        """
        # キャッシュに存在すればそれを返す
        if prompt_key in self._prompts_cache:
            return self._prompts_cache[prompt_key]

        # 新しいプロンプト管理システムから読み込み
        if prompt_key in PROMPT_MAPPING:
            try:
                # 新しいシステムでプロンプトを取得
                new_prompt_path = PROMPT_MAPPING[prompt_key]
                prompt = self._get_prompt_from_new_system(new_prompt_path)
                self._prompts_cache[prompt_key] = prompt
                return prompt
            except Exception as e:
                logger.warning(
                    f"新システムからの '{prompt_key}' プロンプト読み込みに失敗: {e}"
                )

        try:
            prompt = self._get_prompt_from_new_system(prompt_key)
            self._prompts_cache[prompt_key] = prompt
            return prompt
        except Exception as e:
            logger.error(f"プロンプト '{prompt_key}' の読み込みに失敗: {e}")

        # キーが見つからない場合
        raise ValueError(f"未知のプロンプトキー: {prompt_key}")

    def _get_prompt_from_new_system(self, prompt_path: str) -> str:
        """
        プロンプト管理システムからプロンプトを取得

        Args:
            prompt_path: プロンプトパス (例: "agents.vision.main")

        Returns:
            プロンプト文字列
        """
        if prompt_path in self.loaded_prompts:
            return self.loaded_prompts[prompt_path]

        # プロンプトパスから末尾の.txtを取り除く（もし存在すれば）
        if prompt_path.endswith(".txt"):
            prompt_path = prompt_path[:-4]

        # まず、そのままのパスで試す
        path_parts = prompt_path.split(".")
        file_path = os.path.join(self.root_dir, *path_parts) + ".txt"

        # ファイルが存在しない場合、階層構造を持つパスとして試す
        if not os.path.exists(file_path) and len(path_parts) > 1:
            # 例: agents.root.main を agents/root/main.txt に変換
            file_path = os.path.join(
                self.root_dir, path_parts[0], "/".join(path_parts[1:]) + ".txt"
            )

        # それでもファイルが見つからない場合、ディレクトリ以下に同名のファイルを探す
        if not os.path.exists(file_path) and len(path_parts) > 1:
            # 例: agents.root を agents/root/root.txt に変換
            last_part = path_parts[-1]
            file_path = os.path.join(
                self.root_dir,
                "/".join(path_parts[:-1]),
                last_part + ".txt"
            )

        # 設定ファイルを確認
        config_dir = os.path.dirname(file_path)
        config_path = os.path.join(config_dir, "config.yaml")
        variables = {}

        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as config_file:
                    config = yaml.safe_load(config_file)
                    if "variables" in config:
                        variables = config["variables"]
            except Exception as e:
                logger.error(
                    f"設定ファイル '{config_path}' の読み込みに失敗: {e}"
                )

        # プロンプトファイル読み込み
        try:
            if not os.path.exists(file_path):
                logger.error(
                    f"プロンプトファイル '{file_path}' が存在しません"
                )
                return f"Error: prompt file '{prompt_path}' not found"

            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()

            # メタデータの処理
            content, metadata = self._process_metadata(content)

            # extends 継承の処理
            content = self._process_extends_inheritance(content)

            # 従来の継承関係の処理（後方互換性）
            content = self._process_inheritance(content)

            # 変数を統合（メタデータ、設定ファイル、グローバル）
            all_variables = {}
            if metadata.get("variables"):
                all_variables.update(metadata["variables"])
            if variables:
                all_variables.update(variables)
            
            # エージェント固有の変数を読み込み
            agent_variables = self._get_agent_variables(prompt_path)
            if agent_variables:
                all_variables.update(agent_variables)
            
            if self.config and "global_variables" in self.config:
                all_variables.update(self.config["global_variables"])

            # ループ処理（変数置換の前に実行）
            content = self._process_each_loops(content, all_variables)

            # テンプレート処理（変数置換）
            if all_variables:
                content = self._apply_variables(content, all_variables)

            self.loaded_prompts[prompt_path] = content
            return content
        except Exception as e:
            logger.error(f"プロンプト '{prompt_path}' の読み込みに失敗: {e}")
            return f"Error loading prompt {prompt_path}: {str(e)}"

    def _process_metadata(self, content: str) -> tuple[str, dict]:
        """
        YAMLメタデータセクションを処理

        Args:
            content: プロンプト内容

        Returns:
            (メタデータを除去したプロンプト内容, メタデータ辞書)
        """
        # YAMLメタデータセクションを検出
        metadata_pattern = r"^---\s*$(.*?)^---\s*$"
        match = re.search(metadata_pattern, content, re.MULTILINE | re.DOTALL)

        metadata = {}
        if match:
            # メタデータセクションを除去
            yaml_section = match.group(0)
            content = content.replace(yaml_section, "", 1).lstrip()

            # メタデータを解析
            try:
                metadata_content = match.group(1)
                metadata = yaml.safe_load(metadata_content) or {}
                logger.debug(f"メタデータを解析: {metadata}")
            except Exception as e:
                logger.warning(f"メタデータの解析に失敗: {e}")

        return content, metadata

    def _process_extends_inheritance(self, content: str) -> str:
        """
        extends: template_path 形式の継承を処理

        Args:
            content: プロンプト内容

        Returns:
            継承を処理したプロンプト内容
        """
        # メタデータから extends を抽出
        metadata_pattern = r"^---\s*$(.*?)^---\s*$"
        match = re.search(metadata_pattern, content, re.MULTILINE | re.DOTALL)

        if match:
            try:
                metadata_content = match.group(1)
                metadata = yaml.safe_load(metadata_content) or {}

                if "extends" in metadata:
                    base_template_path = metadata["extends"]
                    logger.debug(
                        f"継承テンプレートを処理: {base_template_path}"
                    )

                    # ベーステンプレートを読み込む
                    base_content = self._get_prompt_from_new_system(base_template_path)

                    # メタデータセクションを除去したカスタム内容を取得
                    custom_content = content.replace(
                        match.group(0), "", 1
                    ).lstrip()

                    # ベースとカスタムをマージ
                    return self._process_override_blocks(
                        base_content, custom_content
                    )

            except Exception as e:
                logger.error(f"extends継承の処理に失敗: {e}")

        return content

    def _process_override_blocks(self, base: str, custom: str) -> str:
        """
        {{override: name}} ブロックの処理

        Args:
            base: ベーステンプレート内容
            custom: カスタムプロンプト内容

        Returns:
            オーバーライドを処理したプロンプト内容
        """
        # ベーステンプレートの {{block: name}} パターンを検索
        base_block_pattern = (
            r"\{\{block:\s*([a-zA-Z0-9_]+)\s*\}\}(.*?)\{\{/block\}\}"
        )
        base_blocks = {}

        # ベーステンプレートのブロックを抽出
        for match in re.finditer(base_block_pattern, base, re.DOTALL):
            block_name = match.group(1)
            block_content = match.group(2)
            base_blocks[block_name] = {
                "content": block_content,
                "full_match": match.group(0),
            }
            logger.debug(f"ベースブロックを発見: {block_name}")

        result = base

        # カスタム内容の {{override: name}} パターンを検索
        override_pattern = (
            r"\{\{override:\s*([a-zA-Z0-9_]+)\s*\}\}(.*?)\{\{/override\}\}"
        )

        for match in re.finditer(override_pattern, custom, re.DOTALL):
            block_name = match.group(1)
            override_content = match.group(2).strip()

            logger.debug(f"オーバーライドブロックを発見: {block_name}")

            if block_name in base_blocks:
                # ベースのブロックをオーバーライド内容で置換
                result = result.replace(
                    base_blocks[block_name]["full_match"], override_content
                )
                logger.debug(f"ブロック '{block_name}' をオーバーライド")
            else:
                logger.warning(
                    f"オーバーライド対象のブロック '{block_name}' がベーステンプレートに見つかりません"
                )

        # カスタム内容からオーバーライドブロックを除去した残りの内容を追加
        remaining_custom = custom
        for match in re.finditer(override_pattern, custom, re.DOTALL):
            remaining_custom = remaining_custom.replace(match.group(0), "")

        remaining_custom = remaining_custom.strip()
        if remaining_custom:
            result += "\n\n" + remaining_custom

        return result

    def _process_each_loops(self, content: str, variables: dict) -> str:
        """
        {{#each array}} ループの処理

        Args:
            content: プロンプト内容
            variables: 置換する変数の辞書

        Returns:
            ループを処理したプロンプト内容
        """
        # {{#each variable_name}} ... {{/each}} パターンを検索
        each_pattern = (
            r"\{\{#each\s+([a-zA-Z0-9_\.]+)\s*\}\}(.*?)\{\{/each\}\}"
        )

        def replace_each_block(match):
            var_path = match.group(1)
            template_content = match.group(2)

            # ネストした変数パスをサポート (例: forbidden_actions)
            var_value = self._get_nested_variable(variables, var_path)

            if not isinstance(var_value, (list, tuple)):
                logger.warning(
                    f"{{{{#each {var_path}}}}} の変数が配列ではありません: {type(var_value)}"
                )
                return f"<!-- Error: {var_path} is not an array -->"

            result = []
            for index, item in enumerate(var_value):
                # テンプレート内容を展開
                item_content = template_content

                # {{this}} を現在のアイテムで置換
                item_content = item_content.replace("{{this}}", str(item))

                # {{@index}} をインデックスで置換
                item_content = item_content.replace("{{@index}}", str(index))

                # {{@last}} を最後の要素かどうかで置換
                is_last = index == len(var_value) - 1

                # {{#unless @last}} ... {{/unless}} パターンを処理
                unless_last_pattern = (
                    r"\{\{#unless\s+@last\s*\}\}(.*?)\{\{/unless\}\}"
                )

                def replace_unless_last(unless_match):
                    unless_content = unless_match.group(1)
                    return unless_content if not is_last else ""

                item_content = re.sub(
                    unless_last_pattern,
                    replace_unless_last,
                    item_content,
                    flags=re.DOTALL,
                )

                result.append(item_content)

            return "".join(result)

        # すべての each ブロックを処理
        return re.sub(
            each_pattern, replace_each_block, content, flags=re.DOTALL
        )

    def _get_nested_variable(self, variables: dict, var_path: str) -> Any:
        """
        ネストした変数パスから値を取得

        Args:
            variables: 変数辞書
            var_path: 変数パス (例: "user.name" or "forbidden_actions")

        Returns:
            変数の値
        """
        parts = var_path.split(".")
        current = variables

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                logger.warning(f"変数パス '{var_path}' が見つかりません")
                return None

        return current

    def _apply_variables(self, content: str, variables: dict) -> str:
        """
        変数を適用

        Args:
            content: プロンプト内容
            variables: 置換する変数の辞書

        Returns:
            変数を置換したプロンプト内容
        """

        def replace_variable(match):
            var_path = match.group(1)
            value = self._get_nested_variable(variables, var_path)

            if value is None:
                logger.warning(f"変数 '{var_path}' が見つかりません")
                return f"{{{{UNDEFINED: {var_path}}}}}"

            return str(value)

        # {{variable_name}} または {{nested.variable}} パターンを置換
        pattern = r"\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}"
        return re.sub(pattern, replace_variable, content)

    def _process_inheritance(self, content: str) -> str:
        """
        継承関係を処理（従来形式）

        Args:
            content: プロンプト内容

        Returns:
            継承を処理したプロンプト内容
        """
        # {{extend: templates.agent_base}} のようなパターンを検出
        extend_pattern = r"\{\{extend:\s*([a-zA-Z0-9_.]+)\s*\}\}"
        match = re.search(extend_pattern, content)

        if match:
            base_path = match.group(1)
            base_content = self._get_prompt_from_new_system(base_path)
            # 拡張マーカーを削除
            content = re.sub(extend_pattern, "", content)
            # ベースにカスタム内容を適用
            return self._merge_contents(base_content, content)

        return content

    def _merge_contents(self, base: str, custom: str) -> str:
        """
        ベースと拡張コンテンツをマージ（従来形式）

        Args:
            base: ベースプロンプト内容
            custom: カスタムプロンプト内容

        Returns:
            マージされたプロンプト内容
        """
        # {{block: name}}...{{/block}} パターンを処理
        block_pattern = (
            r"\{\{block:\s*([a-zA-Z0-9_]+)\s*\}\}(.*?)\{\{/block\}\}"
        )
        blocks = re.finditer(block_pattern, base, re.DOTALL)

        for match in blocks:
            block_name = match.group(1)
            # 使用していないが、将来の拡張のために変数を保持
            _ = match.group(2)  # default_content

            # カスタム内容にオーバーライドがあるか確認
            override_pattern = (
                r"\{\{override:\s*"
                + re.escape(block_name)
                + r"\s*\}\}(.*?)\{\{/override\}\}"
            )
            override_match = re.search(override_pattern, custom, re.DOTALL)

            if override_match:
                # オーバーライドで置換
                override_content = override_match.group(1)
                base = base.replace(match.group(0), override_content)
                # 使用したオーバーライドセクションを削除
                custom = re.sub(override_pattern, "", custom)

        # ベースにないカスタム内容を追加
        return base + "\n\n" + custom

    def _get_agent_variables(self, prompt_path: str) -> dict:
        """
        エージェント固有の変数を取得

        Args:
            prompt_path: プロンプトパス (例: "agents.youtube_search.main")

        Returns:
            エージェント固有の変数辞書
        """
        if not self.config or "agents" not in self.config:
            return {}

        # プロンプトパスからエージェント名を抽出
        path_parts = prompt_path.split(".")
        if len(path_parts) < 2:
            return {}

        agent_name = path_parts[1]  # "agents.youtube_search.main" → "youtube_search"
        
        # エージェント設定を検索
        agents_config = self.config["agents"]
        
        # 直接マッチ
        if agent_name in agents_config:
            agent_config = agents_config[agent_name]
            if "variables" in agent_config:
                return agent_config["variables"]
        
        # ネストした設定を検索
        for parent_agent, parent_config in agents_config.items():
            if isinstance(parent_config, dict) and agent_name in parent_config:
                agent_config = parent_config[agent_name]
                if "variables" in agent_config:
                    return agent_config["variables"]
        
        return {}


    def get_all_prompts(self) -> Dict[str, str]:
        """すべてのプロンプトを一括で読み込む

        新しい管理システムからプロンプトの読み込みを試み、失敗した場合は
        従来の方法にフォールバックします。

        Returns:
            Dict[str, str]: キーとプロンプトテキストのディクショナリ
        """
        # キャッシュをクリア（確実に最新を読み込むため）
        self._prompts_cache = {}

        # すべてのプロンプトを読み込む
        prompts = {}
        for key, prompt_path in PROMPT_MAPPING.items():
            prompts[key] = self.get_prompt(key)

        return prompts

    def get_agent_prompts(self, agent_name: str) -> Dict[str, str]:
        """
        エージェント用のすべてのプロンプトを辞書で取得

        Args:
            agent_name: エージェント名（例: "root", "calculator"）

        Returns:
            プロンプト名とその内容のマッピング辞書
        """
        config_path = os.path.join(
            self.root_dir, "agents", agent_name, "config.yaml"
        )
        prompts = {}

        if not os.path.exists(config_path):
            logger.error(
                f"エージェント '{agent_name}' の設定ファイルが見つかりません"
            )
            return prompts

        try:
            with open(config_path, "r", encoding="utf-8") as file:
                config = yaml.safe_load(file)

            if "prompts" in config:
                for prompt_item in config["prompts"]:
                    for key, path in prompt_item.items():
                        prompts[key] = self.get_prompt(path.replace("/", "."))

            return prompts
        except Exception as e:
            logger.error(
                f"エージェント '{agent_name}' のプロンプト読み込みに失敗: {e}"
            )
            return {}
# シングルトンインスタンスを公開
PromptManager = PromptManager