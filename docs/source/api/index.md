# CellMage API Reference

This section provides detailed API documentation for CellMage's modules and classes.

## Core APIs

```{eval-rst}
.. autosummary::
    :toctree: generated

    cellmage.chat_manager
    cellmage.conversation_manager
    cellmage.history_manager
    cellmage.models
    cellmage.config
    cellmage.exceptions
```

## LLM Adapters

```{eval-rst}
.. autosummary::
    :toctree: generated

    cellmage.adapters
    cellmage.adapters.direct_client
    cellmage.adapters.langchain_client
    cellmage.interfaces
```

## Storage APIs

```{eval-rst}
.. autosummary::
    :toctree: generated

    cellmage.storage
    cellmage.storage.memory_store
    cellmage.storage.markdown_store
    cellmage.storage.sqlite_store
```

## Resources

```{eval-rst}
.. autosummary::
    :toctree: generated

    cellmage.resources.file_loader
    cellmage.resources.memory_loader
```

## Utilities

```{eval-rst}
.. autosummary::
    :toctree: generated

    cellmage.utils.date_utils
    cellmage.utils.file_utils
    cellmage.utils.logging_utils
    cellmage.utils.markdown_utils
    cellmage.utils.model_utils
    cellmage.utils.token_counter
```

## Context Providers

```{eval-rst}
.. autosummary::
    :toctree: generated

    cellmage.context_providers
    cellmage.context_providers.ipython_context_provider
```

## Integrations

```{eval-rst}
.. autosummary::
    :toctree: generated

    cellmage.integrations
    cellmage.integrations.base_magic
    cellmage.integrations.confluence_magic
    cellmage.integrations.github_magic
    cellmage.integrations.gitlab_magic
    cellmage.integrations.jira_magic
    cellmage.integrations.sqlite_magic
    cellmage.integrations.webcontent_magic
```

## Magic Commands

```{eval-rst}
.. autosummary::
    :toctree: generated

    cellmage.magic_commands
    cellmage.magic_commands.ipython
    cellmage.magic_commands.ipython.common
    cellmage.magic_commands.ipython.config_magic
    cellmage.magic_commands.ipython.llm_magic
    cellmage.magic_commands.ipython.ambient_magic
```

## Ambient Mode

```{eval-rst}
.. autosummary::
    :toctree: generated

    cellmage.ambient_mode
```
