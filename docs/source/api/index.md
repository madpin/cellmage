# CellMage API Reference

This section provides detailed API documentation for CellMage's modules and classes.

```{toctree}
:maxdepth: 2
:caption: API Reference
:hidden:

generated/cellmage.chat_manager
generated/cellmage.conversation_manager
generated/cellmage.history_manager
generated/cellmage.models
generated/cellmage.config
generated/cellmage.exceptions
generated/cellmage.adapters
generated/cellmage.adapters.direct_client
generated/cellmage.adapters.langchain_client
generated/cellmage.interfaces
generated/cellmage.storage
generated/cellmage.storage.memory_store
generated/cellmage.storage.markdown_store
generated/cellmage.storage.sqlite_store
generated/cellmage.resources.file_loader
generated/cellmage.resources.memory_loader
generated/cellmage.utils.date_utils
generated/cellmage.utils.file_utils
generated/cellmage.utils.logging
generated/cellmage.utils.token_utils
generated/cellmage.utils.confluence_utils
generated/cellmage.utils.github_utils
generated/cellmage.utils.gitlab_utils
generated/cellmage.utils.jira_utils
generated/cellmage.utils.gdocs_utils
generated/cellmage.utils.webcontent_utils
generated/cellmage.context_providers
generated/cellmage.context_providers.ipython_context_provider
generated/cellmage.integrations
generated/cellmage.integrations.base_magic
generated/cellmage.integrations.confluence_magic
generated/cellmage.integrations.github_magic
generated/cellmage.integrations.gitlab_magic
generated/cellmage.integrations.jira_magic
generated/cellmage.integrations.sqlite_magic
generated/cellmage.integrations.webcontent_magic
generated/cellmage.magic_commands
generated/cellmage.magic_commands.ipython
generated/cellmage.magic_commands.ipython.common
generated/cellmage.magic_commands.ipython.config_magic
generated/cellmage.magic_commands.ipython.llm_magic
generated/cellmage.magic_commands.ipython.ambient_magic
generated/cellmage.ambient_mode
```

## Core APIs

```{eval-rst}
.. autosummary::
    :toctree: generated

    cellmage.chat_manager
    cellmage.conversation_manager
    .. deprecated:: 0.9.0
       The `history_manager` module is deprecated. Use `conversation_manager` instead.
    cellmage.history_manager
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
    cellmage.utils.logging
    cellmage.utils.token_utils
    cellmage.utils.confluence_utils
    cellmage.utils.github_utils
    cellmage.utils.gitlab_utils
    cellmage.utils.jira_utils
    cellmage.utils.gdocs_utils
    cellmage.utils.webcontent_utils
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
