#!/usr/bin/env node
/**
 * MCP Server for WordPress.org REST API (wp-json/wp/v2)
 *
 * Works with self-hosted WordPress (Coolify, etc.)
 * Uses Application Password authentication (Basic Auth).
 *
 * Env vars:
 *   WORDPRESS_SITE_URL      — Site URL (e.g., "https://hemle.blog")
 *   WORDPRESS_USERNAME      — WordPress username
 *   WORDPRESS_APP_PASSWORD  — Application password (from WP Admin → Users → Application Passwords)
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const SITE_URL = (process.env.WORDPRESS_SITE_URL || "https://hemle.blog").replace(/\/+$/, "");
const USERNAME = process.env.WORDPRESS_USERNAME || "";
const APP_PASSWORD = process.env.WORDPRESS_APP_PASSWORD || "";

const API = `${SITE_URL}/wp-json/wp/v2`;

// Basic Auth header from username + application password
const AUTH_HEADER = `Basic ${Buffer.from(`${USERNAME}:${APP_PASSWORD}`).toString("base64")}`;

// ── HTTP helper ─────────────────────────────────────────────

async function wp(method, path, body = null) {
  const url = path.startsWith("http") ? path : `${API}${path}`;
  const headers = {
    Authorization: AUTH_HEADER,
    "Content-Type": "application/json",
    "User-Agent": "mcp-wordpress/2.0",
  };

  const opts = { method, headers };
  if (body && method !== "GET") {
    opts.body = JSON.stringify(body);
  }

  const resp = await fetch(url, opts);
  const data = await resp.json();

  if (!resp.ok) {
    throw new Error(
      `WordPress API ${resp.status}: ${data.message || data.code || JSON.stringify(data)}`
    );
  }
  return data;
}

// ── MCP Server ──────────────────────────────────────────────

const server = new McpServer({
  name: "wordpress",
  version: "2.0.0",
});

// ── Tool: create_post ───────────────────────────────────────

server.tool(
  "wp_create_post",
  "Create a new blog post on WordPress. Supports full HTML content.",
  {
    title: z.string().describe("Post title"),
    content: z.string().describe("Post content (HTML)"),
    status: z
      .enum(["publish", "draft", "pending", "private"])
      .default("draft")
      .describe("Post status"),
    categories: z
      .array(z.number())
      .optional()
      .describe("Array of category IDs"),
    tags: z
      .array(z.number())
      .optional()
      .describe("Array of tag IDs"),
    excerpt: z.string().optional().describe("Post excerpt for SEO"),
    slug: z.string().optional().describe("URL slug"),
    format: z
      .enum(["standard", "aside", "image", "video", "quote", "link", "gallery", "status", "chat", "audio"])
      .default("standard")
      .describe("Post format"),
    featured_media: z.number().optional().describe("Featured image media ID"),
  },
  async ({ title, content, status, categories, tags, excerpt, slug, format, featured_media }) => {
    const body = { title, content, status, format };
    if (categories) body.categories = categories;
    if (tags) body.tags = tags;
    if (excerpt) body.excerpt = excerpt;
    if (slug) body.slug = slug;
    if (featured_media) body.featured_media = featured_media;

    const post = await wp("POST", "/posts", body);

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              id: post.id,
              url: post.link,
              status: post.status,
              title: post.title?.rendered,
              slug: post.slug,
            },
            null,
            2
          ),
        },
      ],
    };
  }
);

// ── Tool: update_post ───────────────────────────────────────

server.tool(
  "wp_update_post",
  "Update an existing post or page by ID.",
  {
    post_id: z.number().describe("Post or page ID to update"),
    type: z.enum(["posts", "pages"]).default("posts").describe("Endpoint: posts or pages"),
    title: z.string().optional().describe("New title"),
    content: z.string().optional().describe("New content (HTML)"),
    status: z
      .enum(["publish", "draft", "pending", "private", "trash"])
      .optional()
      .describe("New status"),
    categories: z.array(z.number()).optional().describe("Category IDs"),
    tags: z.array(z.number()).optional().describe("Tag IDs"),
    excerpt: z.string().optional().describe("New excerpt"),
  },
  async ({ post_id, type, title, content, status, categories, tags, excerpt }) => {
    const body = {};
    if (title) body.title = title;
    if (content) body.content = content;
    if (status) body.status = status;
    if (categories) body.categories = categories;
    if (tags) body.tags = tags;
    if (excerpt) body.excerpt = excerpt;

    const post = await wp("POST", `/${type}/${post_id}`, body);

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            { id: post.id, url: post.link, status: post.status, title: post.title?.rendered },
            null,
            2
          ),
        },
      ],
    };
  }
);

// ── Tool: list_posts ────────────────────────────────────────

server.tool(
  "wp_list_posts",
  "List recent posts. Returns title, ID, URL, status, date.",
  {
    per_page: z.number().default(10).describe("Number of posts to return (max 100)"),
    status: z
      .enum(["publish", "draft", "pending", "private", "any"])
      .default("any")
      .describe("Filter by status"),
    categories: z.number().optional().describe("Filter by category ID"),
    search: z.string().optional().describe("Search posts by keyword"),
    type: z.enum(["posts", "pages"]).default("posts").describe("Endpoint: posts or pages"),
  },
  async ({ per_page, status, categories, search, type }) => {
    const params = new URLSearchParams({ per_page: String(per_page), status });
    if (categories) params.set("categories", String(categories));
    if (search) params.set("search", search);

    const data = await wp("GET", `/${type}?${params}`);

    const posts = (Array.isArray(data) ? data : []).map((p) => ({
      id: p.id,
      title: p.title?.rendered,
      url: p.link,
      status: p.status,
      date: p.date,
      slug: p.slug,
    }));

    return {
      content: [{ type: "text", text: JSON.stringify(posts, null, 2) }],
    };
  }
);

// ── Tool: get_post ──────────────────────────────────────────

server.tool(
  "wp_get_post",
  "Get a single post or page by ID, including full content.",
  {
    post_id: z.number().describe("Post or page ID"),
    type: z.enum(["posts", "pages"]).default("posts").describe("Endpoint"),
  },
  async ({ post_id, type }) => {
    const post = await wp("GET", `/${type}/${post_id}`);
    const content = post.content?.rendered || "";
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              id: post.id,
              title: post.title?.rendered,
              url: post.link,
              status: post.status,
              date: post.date,
              content: content.substring(0, 500) + (content.length > 500 ? "..." : ""),
              excerpt: post.excerpt?.rendered,
              slug: post.slug,
            },
            null,
            2
          ),
        },
      ],
    };
  }
);

// ── Tool: delete_post ───────────────────────────────────────

server.tool(
  "wp_delete_post",
  "Delete (trash) a post or page by ID.",
  {
    post_id: z.number().describe("Post or page ID to delete"),
    type: z.enum(["posts", "pages"]).default("posts").describe("Endpoint"),
    force: z.boolean().default(false).describe("Skip trash and permanently delete"),
  },
  async ({ post_id, type, force }) => {
    const result = await wp("DELETE", `/${type}/${post_id}?force=${force}`);
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            { id: result.id, status: result.status, title: result.title?.rendered },
            null,
            2
          ),
        },
      ],
    };
  }
);

// ── Tool: create_page ───────────────────────────────────────

server.tool(
  "wp_create_page",
  "Create a new page (Home, About, etc.).",
  {
    title: z.string().describe("Page title"),
    content: z.string().describe("Page content (HTML)"),
    status: z
      .enum(["publish", "draft"])
      .default("draft")
      .describe("Page status"),
    slug: z.string().optional().describe("URL slug"),
  },
  async ({ title, content, status, slug }) => {
    const body = { title, content, status };
    if (slug) body.slug = slug;

    const page = await wp("POST", "/pages", body);

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            { id: page.id, url: page.link, status: page.status, title: page.title?.rendered, slug: page.slug },
            null,
            2
          ),
        },
      ],
    };
  }
);

// ── Tool: manage_categories ─────────────────────────────────

server.tool(
  "wp_manage_categories",
  "List existing categories or create a new one.",
  {
    action: z.enum(["list", "create"]).describe("Action to perform"),
    name: z.string().optional().describe("Category name (required for create)"),
    description: z.string().optional().describe("Category description"),
    slug: z.string().optional().describe("Category slug"),
  },
  async ({ action, name, description, slug }) => {
    if (action === "list") {
      const cats = await wp("GET", "/categories?per_page=100");
      const list = (Array.isArray(cats) ? cats : []).map((c) => ({
        id: c.id,
        name: c.name,
        slug: c.slug,
        count: c.count,
      }));
      return { content: [{ type: "text", text: JSON.stringify(list, null, 2) }] };
    }

    if (!name) throw new Error("name is required for create action");
    const body = { name };
    if (description) body.description = description;
    if (slug) body.slug = slug;

    const cat = await wp("POST", "/categories", body);
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({ id: cat.id, name: cat.name, slug: cat.slug }, null, 2),
        },
      ],
    };
  }
);

// ── Tool: manage_tags ───────────────────────────────────────

server.tool(
  "wp_manage_tags",
  "List existing tags or create a new one.",
  {
    action: z.enum(["list", "create"]).describe("Action to perform"),
    name: z.string().optional().describe("Tag name (required for create)"),
    slug: z.string().optional().describe("Tag slug"),
  },
  async ({ action, name, slug }) => {
    if (action === "list") {
      const tags = await wp("GET", "/tags?per_page=100");
      const list = (Array.isArray(tags) ? tags : []).map((t) => ({
        id: t.id,
        name: t.name,
        slug: t.slug,
        count: t.count,
      }));
      return { content: [{ type: "text", text: JSON.stringify(list, null, 2) }] };
    }

    if (!name) throw new Error("name is required for create action");
    const body = { name };
    if (slug) body.slug = slug;

    const tag = await wp("POST", "/tags", body);
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({ id: tag.id, name: tag.name, slug: tag.slug }, null, 2),
        },
      ],
    };
  }
);

// ── Tool: get_site_info ─────────────────────────────────────

server.tool(
  "wp_get_site_info",
  "Get WordPress site information (name, description, URL, timezone).",
  {},
  async () => {
    const site = await wp("GET", `${SITE_URL}/wp-json`);
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              name: site.name,
              description: site.description,
              url: site.url,
              home: site.home,
              gmt_offset: site.gmt_offset,
              timezone_string: site.timezone_string,
              namespaces: site.namespaces?.length,
            },
            null,
            2
          ),
        },
      ],
    };
  }
);

// ── Tool: publish_trend_report ──────────────────────────────

server.tool(
  "wp_publish_trend_report",
  "Publish a trend intelligence report to hemle.blog. Reads the WP-formatted HTML file and creates a WordPress post.",
  {
    html_file: z.string().describe("Path to the WP-formatted HTML report file"),
    title: z.string().describe("Post title"),
    status: z.enum(["publish", "draft"]).default("draft").describe("Post status"),
    category_ids: z
      .array(z.number())
      .optional()
      .describe("Category IDs to assign"),
    tags: z
      .string()
      .optional()
      .describe("Comma-separated tag names (will be created if needed)"),
    excerpt: z.string().optional().describe("SEO excerpt"),
  },
  async ({ html_file, title, status, category_ids, tags, excerpt }) => {
    const fs = await import("node:fs/promises");
    const content = await fs.readFile(html_file, "utf-8");

    const body = { title, content, status };
    if (category_ids) body.categories = category_ids;
    if (excerpt) body.excerpt = excerpt;

    // Handle tags: look up or create each tag by name
    if (tags) {
      const tagNames = tags.split(",").map((t) => t.trim()).filter(Boolean);
      const tagIds = [];
      for (const tagName of tagNames) {
        // Search existing
        const existing = await wp("GET", `/tags?search=${encodeURIComponent(tagName)}&per_page=1`);
        if (Array.isArray(existing) && existing.length > 0 && existing[0].name.toLowerCase() === tagName.toLowerCase()) {
          tagIds.push(existing[0].id);
        } else {
          // Create new tag
          const newTag = await wp("POST", "/tags", { name: tagName });
          tagIds.push(newTag.id);
        }
      }
      body.tags = tagIds;
    }

    const post = await wp("POST", "/posts", body);

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              id: post.id,
              url: post.link,
              status: post.status,
              title: post.title?.rendered,
              slug: post.slug,
              message: `Post ${status === "publish" ? "published" : "saved as draft"} successfully!`,
            },
            null,
            2
          ),
        },
      ],
    };
  }
);

// ── Start ───────────────────────────────────────────────────

const transport = new StdioServerTransport();
await server.connect(transport);
