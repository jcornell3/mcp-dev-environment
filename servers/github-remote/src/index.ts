#!/usr/bin/env node

/**
 * GitHub Remote MCP Server
 *
 * Provides MCP tools for:
 * - Repository management (search, create, read files)
 * - Issues and Pull Requests (list, create, update)
 * - GitHub Actions (list runs, get usage, list artifacts)
 *
 * Requires:
 * - GITHUB_PERSONAL_ACCESS_TOKEN environment variable
 * - MCP_API_KEY for HTTP/SSE authentication (when used with bridge)
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
  TextContent,
} from '@modelcontextprotocol/sdk/types.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { Octokit } from '@octokit/rest';
import * as fs from 'fs';
import * as path from 'path';

// Environment variables
const GITHUB_TOKEN = process.env.GITHUB_PERSONAL_ACCESS_TOKEN;
const MCP_API_KEY = process.env.MCP_API_KEY || 'default-api-key';
const DEMO_MODE = !GITHUB_TOKEN;

console.log('[GitHub MCP] Initializing GitHub Remote MCP Server');
console.log('[GitHub MCP] GitHub Token Status: ' + (GITHUB_TOKEN ? 'Configured' : 'Demo Mode (read-only)'));
console.log('[GitHub MCP] ⚠️  WARNING: Set GITHUB_PERSONAL_ACCESS_TOKEN to enable write operations');

// Initialize Octokit (even without token, can be used for demo)
const octokit = new Octokit({
  auth: GITHUB_TOKEN || undefined,
});

// Create MCP server
const server = new Server({
  name: 'github-remote',
  version: '1.0.0',
}, {
  capabilities: {
    tools: {},
  },
});

// Define tools
const tools = [
  {
    name: 'search_repositories',
    description: 'Search for GitHub repositories by query',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Search query (e.g., "language:typescript stars:>1000")',
        },
        per_page: {
          type: 'number',
          description: 'Results per page (default: 10, max: 100)',
          default: 10,
        },
      },
      required: ['query'],
    },
  },
  {
    name: 'get_file_contents',
    description: 'Get the contents of a file from a GitHub repository',
    inputSchema: {
      type: 'object',
      properties: {
        owner: {
          type: 'string',
          description: 'Repository owner username',
        },
        repo: {
          type: 'string',
          description: 'Repository name',
        },
        path: {
          type: 'string',
          description: 'File path in repository',
        },
      },
      required: ['owner', 'repo', 'path'],
    },
  },
  {
    name: 'list_commits',
    description: 'List commits in a GitHub repository',
    inputSchema: {
      type: 'object',
      properties: {
        owner: {
          type: 'string',
          description: 'Repository owner username',
        },
        repo: {
          type: 'string',
          description: 'Repository name',
        },
        per_page: {
          type: 'number',
          description: 'Commits per page (default: 10, max: 100)',
          default: 10,
        },
      },
      required: ['owner', 'repo'],
    },
  },
  {
    name: 'create_repository',
    description: 'Create a new GitHub repository',
    inputSchema: {
      type: 'object',
      properties: {
        name: {
          type: 'string',
          description: 'Repository name',
        },
        description: {
          type: 'string',
          description: 'Repository description',
        },
        private: {
          type: 'boolean',
          description: 'Make repository private (default: false)',
          default: false,
        },
      },
      required: ['name'],
    },
  },
  {
    name: 'create_or_update_file',
    description: 'Create or update a file in a GitHub repository',
    inputSchema: {
      type: 'object',
      properties: {
        owner: {
          type: 'string',
          description: 'Repository owner username',
        },
        repo: {
          type: 'string',
          description: 'Repository name',
        },
        path: {
          type: 'string',
          description: 'File path in repository',
        },
        content: {
          type: 'string',
          description: 'File content (base64 encoded)',
        },
        message: {
          type: 'string',
          description: 'Commit message',
        },
        branch: {
          type: 'string',
          description: 'Branch name (default: main)',
          default: 'main',
        },
        sha: {
          type: 'string',
          description: 'File SHA (required if updating existing file)',
        },
      },
      required: ['owner', 'repo', 'path', 'content', 'message'],
    },
  },
  {
    name: 'list_issues',
    description: 'List issues in a GitHub repository',
    inputSchema: {
      type: 'object',
      properties: {
        owner: {
          type: 'string',
          description: 'Repository owner username',
        },
        repo: {
          type: 'string',
          description: 'Repository name',
        },
        state: {
          type: 'string',
          enum: ['open', 'closed', 'all'],
          description: 'Filter by state (default: open)',
          default: 'open',
        },
        per_page: {
          type: 'number',
          description: 'Issues per page (default: 10, max: 100)',
          default: 10,
        },
      },
      required: ['owner', 'repo'],
    },
  },
  {
    name: 'create_issue',
    description: 'Create a new issue in a GitHub repository',
    inputSchema: {
      type: 'object',
      properties: {
        owner: {
          type: 'string',
          description: 'Repository owner username',
        },
        repo: {
          type: 'string',
          description: 'Repository name',
        },
        title: {
          type: 'string',
          description: 'Issue title',
        },
        body: {
          type: 'string',
          description: 'Issue description (markdown)',
        },
        labels: {
          type: 'array',
          items: { type: 'string' },
          description: 'Issue labels',
        },
      },
      required: ['owner', 'repo', 'title'],
    },
  },
  {
    name: 'update_issue',
    description: 'Update an existing issue in a GitHub repository',
    inputSchema: {
      type: 'object',
      properties: {
        owner: {
          type: 'string',
          description: 'Repository owner username',
        },
        repo: {
          type: 'string',
          description: 'Repository name',
        },
        issue_number: {
          type: 'number',
          description: 'Issue number',
        },
        state: {
          type: 'string',
          enum: ['open', 'closed'],
          description: 'Issue state',
        },
        body: {
          type: 'string',
          description: 'Issue description (markdown)',
        },
      },
      required: ['owner', 'repo', 'issue_number'],
    },
  },
  {
    name: 'list_pull_requests',
    description: 'List pull requests in a GitHub repository',
    inputSchema: {
      type: 'object',
      properties: {
        owner: {
          type: 'string',
          description: 'Repository owner username',
        },
        repo: {
          type: 'string',
          description: 'Repository name',
        },
        state: {
          type: 'string',
          enum: ['open', 'closed', 'all'],
          description: 'Filter by state (default: open)',
          default: 'open',
        },
        per_page: {
          type: 'number',
          description: 'PRs per page (default: 10, max: 100)',
          default: 10,
        },
      },
      required: ['owner', 'repo'],
    },
  },
  {
    name: 'get_pull_request',
    description: 'Get details of a specific pull request',
    inputSchema: {
      type: 'object',
      properties: {
        owner: {
          type: 'string',
          description: 'Repository owner username',
        },
        repo: {
          type: 'string',
          description: 'Repository name',
        },
        pull_number: {
          type: 'number',
          description: 'Pull request number',
        },
      },
      required: ['owner', 'repo', 'pull_number'],
    },
  },
  {
    name: 'list_workflow_runs',
    description: 'List GitHub Actions workflow runs for a repository',
    inputSchema: {
      type: 'object',
      properties: {
        owner: {
          type: 'string',
          description: 'Repository owner username',
        },
        repo: {
          type: 'string',
          description: 'Repository name',
        },
        status: {
          type: 'string',
          enum: ['completed', 'action_required', 'cancelled', 'failure', 'neutral', 'skipped', 'stale', 'success', 'timed_out', 'in_progress', 'queued', 'requested', 'waiting'],
          description: 'Filter by run status',
        },
        per_page: {
          type: 'number',
          description: 'Runs per page (default: 10, max: 100)',
          default: 10,
        },
      },
      required: ['owner', 'repo'],
    },
  },
  {
    name: 'get_workflow_run_usage',
    description: 'Get GitHub Actions usage for a specific workflow run',
    inputSchema: {
      type: 'object',
      properties: {
        owner: {
          type: 'string',
          description: 'Repository owner username',
        },
        repo: {
          type: 'string',
          description: 'Repository name',
        },
        run_id: {
          type: 'number',
          description: 'Workflow run ID',
        },
      },
      required: ['owner', 'repo', 'run_id'],
    },
  },
  {
    name: 'list_workflow_run_artifacts',
    description: 'List artifacts from a GitHub Actions workflow run',
    inputSchema: {
      type: 'object',
      properties: {
        owner: {
          type: 'string',
          description: 'Repository owner username',
        },
        repo: {
          type: 'string',
          description: 'Repository name',
        },
        run_id: {
          type: 'number',
          description: 'Workflow run ID',
        },
        per_page: {
          type: 'number',
          description: 'Artifacts per page (default: 10, max: 100)',
          default: 10,
        },
      },
      required: ['owner', 'repo', 'run_id'],
    },
  },
];

// List tools handler
server.setRequestHandler(ListToolsRequestSchema, async () => {
  console.log('[GitHub MCP] Listing available tools');
  return { tools };
});

// Call tool handler
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  console.log('[GitHub MCP] Raw request.params:', JSON.stringify(request.params));
  const { name } = request.params;
  const toolArgs = (request.params as any).arguments || {};
  console.log(`[GitHub MCP] Executing tool: ${name}`);

  try {
    let result;

    switch (name) {
      case 'search_repositories':
        result = await searchRepositories(toolArgs as any);
        break;

      case 'get_file_contents':
        result = await getFileContents(toolArgs as any);
        break;

      case 'list_commits':
        result = await listCommits(toolArgs as any);
        break;

      case 'create_repository':
        result = await createRepository(toolArgs as any);
        break;

      case 'create_or_update_file':
        result = await createOrUpdateFile(toolArgs as any);
        break;

      case 'list_issues':
        result = await listIssues(toolArgs as any);
        break;

      case 'create_issue':
        result = await createIssue(toolArgs as any);
        break;

      case 'update_issue':
        result = await updateIssue(toolArgs as any);
        break;

      case 'list_pull_requests':
        result = await listPullRequests(toolArgs as any);
        break;

      case 'get_pull_request':
        result = await getPullRequest(toolArgs as any);
        break;

      case 'list_workflow_runs':
        result = await listWorkflowRuns(toolArgs as any);
        break;

      case 'get_workflow_run_usage':
        result = await getWorkflowRunUsage(toolArgs as any);
        break;

      case 'list_workflow_run_artifacts':
        result = await listWorkflowRunArtifacts(toolArgs as any);
        break;

      default:
        throw new Error(`Unknown tool: ${name}`);
    }

    console.log(`[GitHub MCP] Tool ${name} succeeded`);
    return {
      content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }],
    };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(`[GitHub MCP] Tool ${name} failed:`, errorMessage);
    return {
      content: [{ type: 'text' as const, text: `Error: ${errorMessage}` }],
      isError: true,
    };
  }
});

// Tool implementations
async function searchRepositories(args: { query: string; per_page?: number }) {
  const response = await octokit.search.repos({
    q: args.query,
    per_page: args.per_page || 10,
  });

  return {
    total_count: response.data.total_count,
    repositories: response.data.items.map((repo) => ({
      name: repo.name,
      owner: repo.owner?.login || 'unknown',
      url: repo.html_url,
      description: repo.description,
      stars: repo.stargazers_count,
      language: repo.language,
      is_private: repo.private,
    })),
  };
}

async function getFileContents(args: { owner: string; repo: string; path: string }) {
  const response = await octokit.repos.getContent({
    owner: args.owner,
    repo: args.repo,
    path: args.path,
  });

  if (Array.isArray(response.data)) {
    throw new Error('Path is a directory, not a file');
  }

  const fileData = response.data as any;
  if (!fileData.content) {
    throw new Error('Cannot read file content');
  }

  const content = Buffer.from(fileData.content, 'base64').toString('utf-8');
  return {
    path: fileData.path,
    size: fileData.size,
    sha: fileData.sha,
    content,
  };
}

async function listCommits(args: { owner: string; repo: string; per_page?: number }) {
  const response = await octokit.repos.listCommits({
    owner: args.owner,
    repo: args.repo,
    per_page: args.per_page || 10,
  });

  return {
    total: response.data.length,
    commits: response.data.map((commit) => ({
      sha: commit.sha,
      message: commit.commit.message,
      author: commit.commit.author?.name,
      date: commit.commit.author?.date,
      url: commit.html_url,
    })),
  };
}

async function createRepository(args: { name: string; description?: string; private?: boolean }) {
  const response = await octokit.repos.createForAuthenticatedUser({
    name: args.name,
    description: args.description || '',
    private: args.private || false,
  });

  return {
    id: response.data.id,
    name: response.data.name,
    owner: response.data.owner.login,
    url: response.data.html_url,
    clone_url: response.data.clone_url,
    is_private: response.data.private,
  };
}

async function createOrUpdateFile(args: {
  owner: string;
  repo: string;
  path: string;
  content: string;
  message: string;
  branch?: string;
  sha?: string;
}) {
  console.log('[GitHub MCP] createOrUpdateFile args:', JSON.stringify(args));

  if (!args.content) {
    throw new Error('content is required');
  }

  // Content is expected to be plain text, convert to base64 for GitHub API
  const contentBase64 = Buffer.from(args.content, 'utf-8').toString('base64');

  let sha: string | undefined = args.sha;

  // If no SHA provided, try to get the existing file's SHA (for updates)
  // If the file doesn't exist, sha will remain undefined (for creates)
  if (!sha) {
    try {
      const existingFile = await octokit.repos.getContent({
        owner: args.owner,
        repo: args.repo,
        path: args.path,
        branch: args.branch || 'main',
      });
      const fileData = existingFile.data as any;
      sha = fileData.sha;
    } catch (e: any) {
      // File doesn't exist, that's okay for creation
      if (e.status !== 404) {
        throw e;
      }
    }
  }

  // Build the request parameters
  const params: any = {
    owner: args.owner,
    repo: args.repo,
    path: args.path,
    message: args.message,
    content: contentBase64,
    branch: args.branch || 'main',
  };

  // Only include sha if we have it (needed for updates, auto-detected from getContent)
  if (sha) {
    params.sha = sha;
  }

  const response = await octokit.repos.createOrUpdateFileContents(params);

  const content = response.data.content as any;
  return {
    commit: {
      sha: response.data.commit.sha,
      message: response.data.commit.message,
      url: response.data.commit.html_url,
    },
    content: {
      path: content?.path,
      sha: content?.sha,
      url: content?.html_url,
    },
  };
}

async function listIssues(args: {
  owner: string;
  repo: string;
  state?: 'open' | 'closed' | 'all';
  per_page?: number;
}) {
  const response = await octokit.issues.listForRepo({
    owner: args.owner,
    repo: args.repo,
    state: args.state || 'open',
    per_page: args.per_page || 10,
  });

  return {
    total: response.data.length,
    issues: response.data.map((issue) => ({
      number: issue.number,
      title: issue.title,
      state: issue.state,
      url: issue.html_url,
      created_at: issue.created_at,
      labels: issue.labels.map((label) => (typeof label === 'string' ? label : label.name)),
    })),
  };
}

async function createIssue(args: {
  owner: string;
  repo: string;
  title: string;
  body?: string;
  labels?: string[];
}) {
  const response = await octokit.issues.create({
    owner: args.owner,
    repo: args.repo,
    title: args.title,
    body: args.body || '',
    labels: args.labels || [],
  });

  return {
    number: response.data.number,
    title: response.data.title,
    url: response.data.html_url,
    created_at: response.data.created_at,
  };
}

async function updateIssue(args: {
  owner: string;
  repo: string;
  issue_number: number;
  state?: 'open' | 'closed';
  body?: string;
}) {
  const response = await octokit.issues.update({
    owner: args.owner,
    repo: args.repo,
    issue_number: args.issue_number,
    state: args.state,
    body: args.body,
  });

  return {
    number: response.data.number,
    title: response.data.title,
    state: response.data.state,
    url: response.data.html_url,
    updated_at: response.data.updated_at,
  };
}

async function listPullRequests(args: {
  owner: string;
  repo: string;
  state?: 'open' | 'closed' | 'all';
  per_page?: number;
}) {
  const response = await octokit.pulls.list({
    owner: args.owner,
    repo: args.repo,
    state: args.state || 'open',
    per_page: args.per_page || 10,
  });

  return {
    total: response.data.length,
    pull_requests: response.data.map((pr) => ({
      number: pr.number,
      title: pr.title,
      state: pr.state,
      author: pr.user?.login,
      url: pr.html_url,
      created_at: pr.created_at,
    })),
  };
}

async function getPullRequest(args: { owner: string; repo: string; pull_number: number }) {
  const response = await octokit.pulls.get({
    owner: args.owner,
    repo: args.repo,
    pull_number: args.pull_number,
  });

  return {
    number: response.data.number,
    title: response.data.title,
    state: response.data.state,
    author: response.data.user?.login,
    body: response.data.body,
    url: response.data.html_url,
    created_at: response.data.created_at,
    merged: response.data.merged,
    merged_at: response.data.merged_at,
  };
}

async function listWorkflowRuns(args: {
  owner: string;
  repo: string;
  status?: string;
  per_page?: number;
}) {
  const response = await octokit.actions.listWorkflowRunsForRepo({
    owner: args.owner,
    repo: args.repo,
    status: args.status as any,
    per_page: args.per_page || 10,
  });

  return {
    total: response.data.total_count,
    workflow_runs: response.data.workflow_runs.map((run) => ({
      id: run.id,
      name: run.name,
      status: run.status,
      conclusion: run.conclusion,
      created_at: run.created_at,
      url: run.html_url,
    })),
  };
}

async function getWorkflowRunUsage(args: { owner: string; repo: string; run_id: number }) {
  const response = await octokit.actions.getWorkflowRunUsage({
    owner: args.owner,
    repo: args.repo,
    run_id: args.run_id,
  });

  return {
    billable: response.data.billable,
    run_duration_ms: response.data.run_duration_ms,
  };
}

async function listWorkflowRunArtifacts(args: {
  owner: string;
  repo: string;
  run_id: number;
  per_page?: number;
}) {
  const response = await octokit.actions.listWorkflowRunArtifacts({
    owner: args.owner,
    repo: args.repo,
    run_id: args.run_id,
    per_page: args.per_page || 10,
  });

  return {
    total: response.data.total_count,
    artifacts: response.data.artifacts.map((artifact) => ({
      id: artifact.id,
      name: artifact.name,
      size_in_bytes: artifact.size_in_bytes,
      created_at: artifact.created_at,
      expires_at: artifact.expires_at,
      url: artifact.url,
    })),
  };
}

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.log('[GitHub MCP] Server connected via stdio transport');
}

main().catch((error) => {
  console.error('[GitHub MCP] Fatal error:', error);
  process.exit(1);
});
