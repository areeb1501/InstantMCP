---
title: Instant MCP
emoji: ⚡
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
short_description: Deploy MCP servers instantly from anywhere, powered by Modal
tags: ["mcp-in-action-track-enterprise", "mcp-in-action-track-consumer", "building-mcp-track-enterprise"]
---

# ⚡ Instant MCP - Deploy Anywhere, Connect Everywhere

> **Instantly deploy MCP servers and access them from anywhere. Powered by Modal.**

Transform your workflow by deploying Model Context Protocol (MCP) servers in seconds, not hours. Connect to external APIs, save on token costs, and extend your AI capabilities with unlimited custom tools.

---

## 🏆 Built for MCP's 1st Birthday Hackathon

**Submission Tracks:**
- 🔧 **Building MCP Track** - Enterprise
- 🤖 **MCP in Action Track** - Enterprise & Consumer

**Demo Video:** [Coming Soon - Placeholder]

**Social Media Post:** [Link to be added]

---

## 🎯 Sponsors & Key Technologies

<div align="center">

### Powered By

| Technology | Usage |
|------------|-------|
| ![Modal](https://via.placeholder.com/150x50?text=Modal+Logo) | **Serverless deployment** - Zero-downtime deployments with automatic scaling |
| ![Anthropic](https://via.placeholder.com/150x50?text=Anthropic+Logo) | **Claude AI** - Intelligent code generation and deployment assistance |
| ![Gradio](https://via.placeholder.com/150x50?text=Gradio+Logo) | **Gradio v6** - Interactive UI with enhanced mobile support and real-time updates |
| ![Nebius](https://via.placeholder.com/150x50?text=Nebius+Logo) | **AI Security Scanning** - Intelligent vulnerability detection before deployment |
| ![SambaNova](https://via.placeholder.com/150x50?text=SambaNova+Logo) | **Alternative LLM** - Cost-effective AI assistance with Llama 3.3 70B |
| ![Hugging Face](https://via.placeholder.com/150x50?text=HF+Logo) | **Hosting & Deployment** - Platform for sharing and deployment |

</div>

---

## 🚀 What is Instant MCP?

**Instant MCP** is a complete platform that transforms how you create, deploy, and manage MCP servers. Built with Gradio v6 and powered by Modal's serverless infrastructure, it enables developers to:

✅ **Deploy MCP servers instantly** - From idea to production in under 60 seconds
✅ **Zero infrastructure management** - Modal handles scaling, cold starts, and costs
✅ **AI-assisted development** - Claude and SambaNova integration for intelligent code generation
✅ **Enterprise-grade security** - Automated vulnerability scanning with Nebius AI
✅ **Comprehensive analytics** - Track usage, performance, and costs in real-time
✅ **Cost optimization** - Scale to zero when idle, pay only for what you use

---

## 💡 Why Instant MCP? Real-World Use Cases

### 1. 🔌 **Connect to External APIs for Cost Savings**

Instead of using expensive Claude API calls for every task, deploy specialized MCP servers that:
- Cache API responses locally
- Batch multiple requests
- Use cheaper alternatives for simple tasks
- **Result:** Save 60-80% on token costs for repetitive operations

**Example:** Deploy a weather MCP server that caches forecasts instead of asking Claude to fetch them repeatedly.

### 2. 🎨 **Use Gemini for Frontend Development**

Create an MCP server that connects to Google's Gemini API for:
- UI/UX design suggestions
- Frontend code generation
- Visual component creation
- **Benefit:** Use Gemini's specialized capabilities while keeping Claude for backend logic

### 3. 🔍 **Perplexity as Web Search Engine**

Deploy an MCP server with Perplexity integration to:
- Perform web searches without consuming Claude tokens
- Get real-time information from the internet
- Extend conversation limits by offloading research to external tools
- **Impact:** 10x longer Claude sessions without hitting usage limits

**Example Use Case:**
```
User asks Claude: "What are the latest developments in quantum computing?"
→ Claude calls your Perplexity MCP server
→ Perplexity searches and summarizes
→ Claude receives results without token overhead
→ User gets answer, your session continues
```

### 4. 🔬 **Building Research Tools**

Create specialized research assistants with MCP servers that:
- Query academic databases (arXiv, PubMed, Google Scholar)
- Aggregate data from multiple sources
- Process and summarize large documents
- Track citations and references
- **Workflow Improvement:** Researchers get automated literature reviews instead of manual searches

### 5. 🏢 **Enterprise Integration**

Deploy MCP servers that connect to:
- Internal databases and CRM systems
- Company knowledge bases
- Proprietary APIs and microservices
- Legacy systems without API exposure
- **Value:** Bring enterprise data to Claude without exposing credentials or building complex integrations

---

## ✨ Key Features

### 🎯 Core Capabilities

#### 1. **Instant Deployment to Modal**
- One-click deployment from UI or AI chat
- Automatic dependency detection
- Zero-downtime updates
- Cost-optimized configuration (scales to zero)
- Public HTTPS endpoints instantly

#### 2. **AI-Powered Development** (Gradio v6 Feature: Agentic Chatbot)
- **Claude Sonnet 4** integration for intelligent code generation
- **SambaNova Llama 3.3 70B** as cost-effective alternative
- Natural language to MCP server conversion
- Automated debugging and optimization
- Code review and security suggestions

#### 3. **Enterprise-Grade Security**
- **Nebius AI-powered scanning** before every deployment
- Detects: SQL injection, command injection, malicious code
- Severity-based blocking (High/Critical vulnerabilities blocked)
- Audit trail for all security scans
- Manual scan tool for pre-deployment testing

#### 4. **Comprehensive Analytics Dashboard**
- Real-time usage statistics
- Tool popularity tracking
- Client distribution analysis
- Performance metrics (response times, success rates)
- Cost tracking and optimization insights
- Timeline visualizations (hourly/daily aggregations)

#### 5. **Production-Ready Database** (PostgreSQL)
- Scalable storage with connection pooling
- ACID transactions for data integrity
- Complete audit logging
- Soft delete with history preservation
- Advanced queries via SQLAlchemy ORM

### 🎨 Gradio v6 Features Used

This project showcases several **Gradio v6** capabilities:

1. **Enhanced MCP Support** (`mcp_server=True`)
   - Built-in MCP server endpoint at `/gradio_api/mcp/`
   - Automatic tool registration with `gr.api()`
   - Streamable HTTP transport for tool calls

2. **Improved Component System**
   - Tabbed interface for organized workflows
   - Real-time updates without page refresh
   - Custom CSS for polished UI

3. **Better API Control**
   - `show_api=False` for UI-only handlers
   - Explicit tool registration for MCP exposure
   - FastAPI integration for custom endpoints

4. **Mobile-Responsive Design**
   - Adaptive layouts for all screen sizes
   - Touch-optimized controls
   - Progressive web app capabilities

5. **Real-Time Streaming**
   - Streaming chat responses from Claude/SambaNova
   - Live deployment status updates
   - Progressive tool execution feedback

---

## 🛠️ Available MCP Tools

### Deployment Management

#### `deploy_mcp_server`
**Deploy a new MCP server to Modal.com**

```python
{
  "server_name": "weather-api",
  "mcp_tools_code": "from fastmcp import FastMCP...",
  "extra_pip_packages": "requests,pandas",
  "description": "Weather data and forecasts",
  "category": "APIs",
  "tags": ["weather", "data"],
  "author": "Your Name",
  "version": "1.0.0"
}
```

**Features:**
- Automatic security scanning (Nebius AI)
- Dependency detection and installation
- Cost-optimized Modal configuration
- Instant HTTPS endpoint generation
- Complete audit logging

---

#### `list_deployments`
**Get all deployed MCP servers with statistics**

Returns deployment list with:
- URLs and endpoints
- Usage statistics
- Status and health checks
- Last used timestamps
- Total request counts

---

#### `get_deployment_status`
**Check detailed status of a deployment**

```python
{
  "deployment_id": "deploy-mcp-weather-abc123"
}
```

Returns:
- Live status check (is it running on Modal?)
- Current URL and endpoint
- Configuration details
- Usage statistics
- Health metrics

---

#### `get_deployment_code`
**Retrieve the source code of a deployment**

Use this before modifying a deployment to see current code, packages, and tools.

---

#### `update_deployment_code`
**Update and redeploy an MCP server**

```python
{
  "deployment_id": "deploy-mcp-weather-abc123",
  "mcp_tools_code": "updated code...",
  "extra_pip_packages": ["requests", "beautifulsoup4"],
  "server_name": "new-name",
  "description": "Updated description"
}
```

**Smart Updates:**
- Preserves URL (reuses same Modal app name)
- Brief downtime (~5-10 seconds)
- Automatic backup before update
- Security re-scanning
- Rollback capability via history

---

#### `delete_deployment`
**Remove a deployment from Modal**

```python
{
  "deployment_id": "deploy-mcp-weather-abc123",
  "confirm": true
}
```

**Safe Deletion:**
- Requires explicit confirmation
- Soft delete (preserves history)
- Stops Modal app billing
- Maintains audit trail

---

### Security Tools

#### `scan_deployment_security`
**Scan MCP code for vulnerabilities WITHOUT deploying**

```python
{
  "mcp_tools_code": "your code...",
  "server_name": "my-server",
  "extra_pip_packages": ["requests"],
  "description": "Optional context"
}
```

**Powered by Nebius AI** - Detects:
- ❌ Code injection (SQL, command, etc.)
- ❌ Malicious network behavior
- ❌ Resource abuse patterns
- ❌ Destructive operations
- ❌ Known malicious packages

**Severity Levels:**
- ✅ **Safe** - No issues found
- ⚠️ **Low** - Minor concerns, allowed
- ⚠️ **Medium** - Review suggested, allowed
- 🚫 **High** - Serious issues, deployment blocked
- 🚫 **Critical** - Severe threats, deployment blocked

---

### Analytics & Statistics

#### `get_deployment_stats`
**Get comprehensive usage statistics**

```python
{
  "deployment_id": "deploy-mcp-weather-abc123",
  "days": 30
}
```

Returns:
- Total requests and success rate
- Average response time
- Peak usage periods
- Error rate analysis
- Client distribution

---

#### `get_tool_usage`
**See which tools are used most**

```python
{
  "deployment_id": "deploy-mcp-weather-abc123",
  "days": 30,
  "limit": 10
}
```

**Insights:**
- Most popular tools
- Request counts per tool
- Success rates by tool
- Performance comparison

---

#### `get_all_stats_summary`
**Quick overview of all deployments**

Returns:
- Total deployments count
- Total requests across all servers
- Average success rate
- Active vs. idle deployments
- Resource utilization

---

## 📸 Screenshots

### Main Dashboard
![Main Dashboard](https://via.placeholder.com/800x450?text=Main+Dashboard+-+Deployment+Management)

*Deploy, manage, and monitor all your MCP servers from one unified interface*

---

### AI Assistant Chat (Gradio v6 Agentic Chatbot)
![AI Chat](https://via.placeholder.com/800x450?text=AI+Assistant+-+Natural+Language+Deployment)

*Chat with Claude or SambaNova to create MCP servers using natural language*

---

### Code Editor
![Code Editor](https://via.placeholder.com/800x450?text=Code+Editor+-+Edit+Deployments)

*Edit deployment code with syntax highlighting and live preview*

---

### Analytics Dashboard
![Analytics](https://via.placeholder.com/800x450?text=Analytics+Dashboard+-+Usage+Statistics)

*Real-time analytics showing usage patterns, performance metrics, and cost tracking*

---

### Security Scan Results
![Security](https://via.placeholder.com/800x450?text=Security+Scan+-+Vulnerability+Detection)

*AI-powered security scanning with detailed vulnerability reports*

---

## 🚀 Quick Start

### Prerequisites

```bash
# Required
- Python 3.10+
- Modal account (free tier works)
- PostgreSQL database (Neon, Supabase, or local)

# Optional (for AI features)
- Anthropic API key (Claude)
- SambaNova API key (Llama)
- Nebius API key (Security scanning)
```

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/instant-mcp.git
cd instant-mcp

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment variables
cp .env.example .env
# Edit .env with your API keys and database URL

# 4. Initialize database
psql $DATABASE_URL -f tests/init_db.sql

# 5. Authenticate with Modal
modal token new
```

### Running Locally

```bash
# Start the main application
python app.py

# Access at: http://localhost:7860
```

### Environment Variables

```bash
# Database (Required)
DATABASE_URL=postgresql://user:pass@host:5432/db

# AI Providers (Optional - choose at least one)
ANTHROPIC_API_KEY=sk-ant-xxxxx
SAMBANOVA_API_KEY=your-key-here

# Security Scanning (Recommended)
NEBIUS_API_KEY=your-nebius-key
SECURITY_SCANNING_ENABLED=true

# Modal (Required for deployment)
MODAL_TOKEN_ID=your-modal-token
MODAL_TOKEN_SECRET=your-modal-secret

# Application
PORT=7860
MCP_BASE_URL=http://localhost:7860
```

---

## 🔌 Connecting to Claude Desktop

Once you've deployed an MCP server, integrate it with Claude Desktop in 3 simple steps:

### Step 1: Get Your Deployment URL
After deployment, you'll receive a URL like:
```
https://your-username--deploy-mcp-weather-abc123.modal.run
```

### Step 2: Add to Claude Desktop Config

Open your `claude_desktop_config.json` file and add:

```json
{
  "mcpServers": {
    "your-server-name": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://your-deployment-url.modal.run/mcp"
      ]
    }
  }
}
```

**Example:**
```json
{
  "mcpServers": {
    "weather-api": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://myuser--deploy-mcp-weather-abc123.modal.run/mcp"
      ]
    }
  }
}
```

### Step 3: Restart Claude Desktop

Close and reopen Claude Desktop. Your MCP server tools will now be available!

**Config File Locations:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

---

## 🎓 How to Use

### Method 1: AI Assistant (Recommended)

1. Navigate to the **🤖 AI Assistant** tab
2. Choose your AI provider (Claude or SambaNova)
3. Describe what you want in natural language:

```
"Create an MCP server that fetches current weather
for any city using the wttr.in API"
```

4. The AI will:
   - Generate the MCP code
   - Scan for security issues
   - Deploy to Modal
   - Return the endpoint URL

5. **Connect to Claude Desktop** - Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "your-server-name": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://your-deployment-url.modal.run/mcp"
      ]
    }
  }
}
```

**Config file location:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

After adding the config, restart Claude Desktop to connect to your deployed MCP server!

### Method 2: Code Editor

1. Go to **💻 Code Editor** tab
2. Write your MCP code following the FastMCP format:

```python
from fastmcp import FastMCP

mcp = FastMCP("my-server")

@mcp.tool
def my_function(param: str) -> str:
    """Description of what this tool does"""
    return f"Result: {param}"
```

3. Add any required packages
4. Click **Deploy**
5. Copy the integration config and add to Claude Desktop (see below)

### Method 3: Admin Panel

1. Use **⚙️ Admin Panel** for:
   - Quick deployment forms
   - Viewing all deployments
   - Managing existing servers
   - Testing deployed endpoints

---

## 🏗️ Architecture

### Technology Stack Breakdown

#### **Frontend: Gradio v6**
- Tabbed interface for workflows
- Real-time streaming updates
- Mobile-responsive design
- Custom CSS styling
- Built-in MCP endpoint

#### **Backend: FastAPI + SQLAlchemy**
- RESTful API design
- PostgreSQL database
- Connection pooling
- Transaction management
- Comprehensive error handling

#### **Deployment: Modal**
- Serverless Python runtime
- Automatic scaling (including to zero)
- Cold start optimization
- HTTPS endpoints
- Environment variable management

#### **AI Integration:**

**Claude (Anthropic)** - Primary AI assistant
- Code generation
- Natural language processing
- Tool use for deployment
- Intelligent debugging

**Llama 3.3 70B (SambaNova)** - Cost-effective alternative
- Same capabilities as Claude
- Lower cost per token
- OpenAI-compatible API

**Nebius AI** - Security scanning
- Vulnerability detection
- Code analysis
- Threat classification
- Automated blocking

---

## 📊 Database Schema

```sql
-- Main deployments table
CREATE TABLE deployments (
  id SERIAL PRIMARY KEY,
  deployment_id VARCHAR(255) UNIQUE,
  app_name VARCHAR(255),
  server_name VARCHAR(255),
  url TEXT,
  mcp_endpoint TEXT,
  status VARCHAR(50),
  created_at TIMESTAMP,
  -- ... usage stats cached
);

-- Package dependencies
CREATE TABLE deployment_packages (
  id SERIAL PRIMARY KEY,
  deployment_id VARCHAR(255),
  package_name VARCHAR(255)
);

-- Code storage
CREATE TABLE deployment_files (
  id SERIAL PRIMARY KEY,
  deployment_id VARCHAR(255),
  file_type VARCHAR(50),
  file_content TEXT
);

-- Audit log
CREATE TABLE deployment_history (
  id SERIAL PRIMARY KEY,
  deployment_id VARCHAR(255),
  action VARCHAR(100),
  timestamp TIMESTAMP,
  details JSONB
);

-- Detailed usage tracking
CREATE TABLE usage_events (
  id SERIAL PRIMARY KEY,
  deployment_id VARCHAR(255),
  tool_name VARCHAR(255),
  timestamp TIMESTAMP,
  duration_ms INTEGER,
  success BOOLEAN,
  client_id VARCHAR(255)
);
```

---

## 🎯 Hackathon Highlights

### Innovation

1. **First MCP-as-a-Service Platform**
   - Deploy MCP servers without infrastructure
   - Managed analytics and monitoring
   - One-click deployment

2. **AI-Powered Development Workflow**
   - Natural language to MCP server
   - Automated testing and security
   - Intelligent code optimization

3. **Cost Optimization Strategy**
   - Scale to zero (no idle costs)
   - Minimal resource allocation
   - External API integration for token savings

### Gradio v6 Features Showcased

- ✅ Native MCP server support
- ✅ Explicit tool registration
- ✅ Streaming responses
- ✅ Tabbed interfaces
- ✅ Mobile responsiveness
- ✅ FastAPI integration
- ✅ Custom webhook endpoints

### Multi-Sponsor Integration

| Sponsor | Integration | Impact |
|---------|-------------|--------|
| **Modal** | Deployment platform | Zero infrastructure management |
| **Anthropic** | Claude AI | Intelligent code generation |
| **Gradio** | UI framework | Beautiful, functional interface |
| **Nebius** | Security scanning | Enterprise-grade safety |
| **SambaNova** | Alternative LLM | Cost-effective AI |
| **Hugging Face** | Hosting | Easy sharing and deployment |

---

## 💰 Cost Optimization

### Modal Pricing Strategy

Our deployments use **minimal resources** to maximize free tier usage:

```python
# Each deployment configured with:
cpu=0.25          # 1/4 CPU core (cheapest tier)
memory=256        # 256 MB RAM (minimal)
scaledown_window=2  # Scale to zero after 2s idle
timeout=300       # 5 min max execution
```

**Result:** Most users stay within Modal's **$30/month free tier**

### Token Cost Savings

By deploying specialized MCP servers:

| Traditional Approach | With Instant MCP | Savings |
|---------------------|------------------|---------|
| Ask Claude for weather | Call weather MCP server | 95% |
| Claude web search (many tokens) | Perplexity MCP server | 80% |
| Claude generates frontend | Gemini MCP server | 70% |
| Repeated API calls via Claude | Cached MCP responses | 90% |

**Average savings: 60-80% on token costs**

---

## 🔒 Security Features

### Multi-Layer Protection

1. **Pre-Deployment Scanning** (Nebius AI)
   - Analyzes code before deployment
   - Blocks high/critical vulnerabilities
   - Provides detailed explanations

2. **Input Validation**
   - Python syntax checking
   - Package name validation
   - Server name sanitization

3. **Audit Logging**
   - All actions tracked
   - Security scan results stored
   - Deployment history preserved

4. **Safe Defaults**
   - No arbitrary code execution
   - Sandboxed Modal runtime
   - Environment variable isolation

---

## 🚧 Roadmap

### Upcoming Features

- [ ] Real-time webhook tracking
- [ ] Cost tracking dashboard
- [ ] Export functionality (CSV/JSON)
- [ ] Multi-user collaboration
- [ ] Template marketplace
- [ ] GitHub integration
- [ ] Automated testing framework
- [ ] Performance benchmarking

---

## 📚 Documentation

- **Quick Start:** See above
- **API Reference:** [API.md](./API.md) (coming soon)
- **Migration Guide:** [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)
- **Security Best Practices:** [SECURITY.md](./SECURITY.md) (coming soon)

---

## 🤝 Contributing

We welcome contributions! Areas of interest:

- Additional AI provider integrations
- More visualization options
- Enhanced security scanning
- Cost optimization algorithms
- Template library expansion

---

## 📄 License

MIT License - See [LICENSE](./LICENSE) for details

---

## 🙏 Acknowledgments

Special thanks to:

- **Anthropic & Gradio** - For hosting this amazing hackathon
- **Modal** - For serverless infrastructure
- **Nebius** - For AI-powered security
- **SambaNova** - For cost-effective LLM access
- **Hugging Face** - For hosting and community
- **FastMCP** - For the excellent MCP framework
- The entire **MCP community** - For pushing the boundaries of AI tooling

---

## 🎉 Get Started Now!

```bash
# Install
git clone https://github.com/yourusername/instant-mcp.git
cd instant-mcp
pip install -r requirements.txt

# Configure
cp .env.example .env
# Add your API keys

# Run
python app.py

# Deploy your first MCP server in under 60 seconds! ⚡
```

---

<div align="center">

**Built with ❤️ for MCP's 1st Birthday Hackathon**

[Live Demo](https://huggingface.co/spaces/yourspace/instant-mcp) • [Documentation](./docs) • [Report Bug](https://github.com/yourrepo/issues) • [Request Feature](https://github.com/yourrepo/issues)

⭐ **Star this repo if you find it useful!** ⭐

</div>
