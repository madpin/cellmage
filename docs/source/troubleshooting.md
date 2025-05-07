# 🔧 Troubleshooting

This guide will help you resolve common issues that you might encounter while using CellMage.

## 🚫 Common Issues & Solutions

### API Connection Issues

**Symptom:** `Unable to connect to API` or `Authentication failed` errors.

**Solutions:**
1. Verify your API key is set correctly:
   ```ipython
   %llm_config --status  # Check if API key is set
   ```
2. Check that your API base URL is correct if using a custom endpoint:
   ```ipython
   %llm_config --api-base https://your-custom-endpoint
   ```
3. Check your internet connection and any required VPN settings.
4. Verify that the service isn't experiencing an outage.

### Missing Personas or Snippets

**Symptom:** `Persona not found` or `Snippet not found` errors.

**Solutions:**
1. Check your persona/snippet directories configuration:
   ```ipython
   %llm_config --status  # View configured directories
   ```
2. Verify that the persona/snippet exists in the specified directory:
   ```bash
   ls ./llm_personas/  # List available personas
   ls ./llm_snippets/  # List available snippets
   ```
3. Try using the absolute path to your persona/snippet:
   ```ipython
   %llm --persona /absolute/path/to/persona.md
   ```

### SQLite Storage Issues

**Symptom:** Database errors or missing conversations.

**Solutions:**
1. Check permissions on the SQLite database file:
   ```bash
   ls -la ~/.cellmage/conversations.db
   ```
2. Ensure the directory exists:
   ```bash
   mkdir -p ~/.cellmage
   ```
3. Verify database integrity:
   ```bash
   sqlite3 ~/.cellmage/conversations.db "PRAGMA integrity_check;"
   ```

### Integration Authentication Problems

**Symptom:** `Authentication failed` when using Jira, Confluence, GitHub, or GitLab.

**Solutions:**
1. Verify that the required environment variables are set:
   ```ipython
   import os
   print("JIRA_API_TOKEN set:", bool(os.environ.get("JIRA_API_TOKEN")))
   # Similar for other service tokens
   ```
2. Check that URLs are correctly formatted (include https://):
   ```ipython
   print(os.environ.get("JIRA_URL"))  # Should start with https://
   ```
3. Regenerate your API tokens/PATs if they might have expired.

### Kernel Restart Required

**Symptom:** Magic commands not working, incorrect behavior after changing configuration.

**Solutions:**
1. Restart the Jupyter kernel:
   ```
   Kernel > Restart
   ```
2. Reinstall the CellMage extension:
   ```ipython
   %reload_ext cellmage
   ```

### Memory Usage Issues

**Symptom:** High memory usage or kernel crashes with large prompts.

**Solutions:**
1. Use streaming responses to reduce memory footprint:
   ```ipython
   %llm --stream "Your prompt here"
   ```
2. Reduce context size by being more selective with snippets:
   ```ipython
   %llm --clear-snippets  # Clear existing snippets
   ```
3. Use smaller models when possible:
   ```ipython
   %llm_config --model gpt-4o-mini
   ```

## 📝 Debugging Tips

### Enable Debug Logging

To get more detailed logs:

```ipython
import logging
from cellmage.utils.logging import setup_logging
setup_logging(level=logging.DEBUG)
```

Logs will be written to `cellmage.log` in your working directory.

### Inspect API Requests

To see the exact requests being sent to the LLM API:

```ipython
%llm_config --debug-mode True
```

This will print the full request and response objects to the log.

### Check Token Usage

To monitor your token usage:

```ipython
%llm_stats  # Shows token usage statistics
```

## 🆘 Getting Help

If you're still encountering issues:

1. Check our [GitHub Issues](https://github.com/madpin/cellmage/issues) to see if your problem has been reported.
2. Create a new issue with:
   - A minimal reproducible example
   - Your environment details (OS, Python version, etc.)
   - Full error messages and logs
   - Steps you've already tried

Our magical community will do its best to help you resolve the issue!
