# Examples

This directory contains example OpenAPI specifications and configurations to help you get started with MCP Generator 2.0.

## 📚 Available Examples

### 1. [Petstore Example](./petstore/) - Complete Example

A full-featured example using the Swagger Petstore API demonstrating:

- Multiple API modules (pet, store, user)
- OAuth2 authentication
- Complex data models
- All HTTP methods (GET, POST, PUT, DELETE)

## 🚀 Quick Start

### Run Any Example

```bash
# From project root
cd examples/petstore
uv run generate-mcp --file openapi.yaml

# Or specify path directly
uv run generate-mcp --file examples/petstore/openapi.yaml
```

### Test Generated Server

```bash
# Navigate to generated output
cd generated_mcp

# Run in STDIO mode
export BACKEND_API_TOKEN="your-token"
python *_mcp_generated.py --transport stdio

# Or run in HTTP mode
python *_mcp_generated.py --transport http --port 8000
```

## 📝 Creating Your Own

1. **Start with an example**

   ```bash
   cp -r examples/minimal-api my-api
   cd my-api
   ```
2. **Modify the OpenAPI spec**

   - Edit `openapi.yaml` with your API definition
   - Update server URLs
   - Define your endpoints and models
3. **Generate your MCP server**

   ```bash
   uv run generate-mcp --file openapi.yaml
   ```
4. **Test and iterate**

   ```bash
   cd generated_mcp
   python *_mcp_generated.py
   ```

## 🎯 Example Use Cases

### REST API Integration

Use the petstore example as a template for any REST API:

- E-commerce APIs
- Social media APIs
- Cloud service APIs
- Custom internal APIs

### Microservices

Generate separate MCP servers for each microservice:

```bash
uv run generate-mcp --file user-service-api.yaml
uv run generate-mcp --file product-service-api.yaml
uv run generate-mcp --file order-service-api.yaml
```

### Third-Party API Wrappers

Wrap existing APIs to make them accessible to AI agents:

- GitHub API
- Stripe API
- Twilio API
- Any OpenAPI-documented API

## 💡 Tips

1. **Start Simple**: Begin with the minimal-api example and gradually add complexity
2. **Validate First**: Use `uv run python scripts/validate_openapi.py` to check your spec
3. **Test Generation**: Generate and test before deploying
4. **Customize Names**: Use `mcp_generator/config.py` to customize tool names
5. **Check Output**: Review generated code before using in production

## 📖 Additional Resources

- [OpenAPI Specification](https://swagger.io/specification/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [Main README](../README.md)

## 🤝 Contributing Examples

Have a great example? We'd love to include it!

1. Create your example in a new directory
2. Include a README.md explaining the use case
3. Add the OpenAPI spec
4. Submit a PR with your example

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details.
