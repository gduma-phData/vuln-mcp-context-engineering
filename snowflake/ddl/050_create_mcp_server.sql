-- GitHub MCP Connector Setup
-- Prerequisites: Create a GitHub App at https://github.com/settings/apps
-- with callback URL: https://identity.snowflake.com/oauth2/callback
-- Note the Client ID and Client Secret after creation.

USE ROLE ACCOUNTADMIN;
USE DATABASE SANDBOX;
USE SCHEMA GDUMA;

-- Step 1: Create API Integration for GitHub OAuth
-- Replace <client_id> and <client_secret> with values from your GitHub App
CREATE OR REPLACE API INTEGRATION github_mcp_api_integration
  API_PROVIDER = external_mcp
  API_ALLOWED_PREFIXES = ('https://api.githubcopilot.com/mcp')
  API_USER_AUTHENTICATION = (
    TYPE = OAUTH2
    OAUTH_CLIENT_ID = '<GITHUB_APP_CLIENT_ID>'
    OAUTH_CLIENT_SECRET = '<GITHUB_APP_CLIENT_SECRET>'
    OAUTH_TOKEN_ENDPOINT = 'https://github.com/login/oauth/access_token'
    OAUTH_AUTHORIZATION_ENDPOINT = 'https://github.com/login/oauth/authorize'
    OAUTH_ALLOWED_SCOPES = ('repo', 'read:org')
    OAUTH_REFRESH_TOKEN_VALIDITY = 86400
  )
  ENABLED = TRUE;

-- Step 2: Create External MCP Server referencing the API Integration
CREATE OR REPLACE EXTERNAL MCP SERVER github_patch_repos
  WITH DISPLAY_NAME = 'GitHub Patch Repos (Infosec CMDB)'
  URL = 'https://api.githubcopilot.com/mcp'
  API_INTEGRATION = github_mcp_api_integration;

-- Step 3: Grant access to the agent role
GRANT USAGE ON EXTERNAL MCP SERVER github_patch_repos TO ROLE ALL_AAI_ARCHITECTS;
GRANT USAGE ON INTEGRATION github_mcp_api_integration TO ROLE ALL_AAI_ARCHITECTS;
