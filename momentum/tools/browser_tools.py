import time
import logging
from typing import Dict, Any, Optional
from momentum.tools.git_tools import BaseTool

logger = logging.getLogger(__name__)

def _get_playwright():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        return None

class BrowserNavigateTool(BaseTool):
    name = "browser_navigate"
    description = "Navigate to a URL in a headless browser and return page title and URL"
    risk_level = "low"
    timeout_seconds = 30
    required_permissions = ["browser.read"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        url = context.get("url") or context.get("target_url", "")
        if not url:
            return {"success": False, "error": "No URL provided", "output": None}
        if dry_run:
            return {"success": True, "output": {"url": url, "title": "dry-run", "dry_run": True}}

        sync_playwright = _get_playwright()
        if not sync_playwright:
            return {"success": False, "error": "playwright not installed", "output": None}

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=self.timeout_seconds * 1000)
                title = page.title()
                final_url = page.url
                browser.close()
            return {"success": True, "output": {"url": final_url, "title": title, "page_loaded": True}}
        except Exception as e:
            return {"success": False, "error": str(e), "output": None}

class BrowserExtractTextTool(BaseTool):
    name = "browser_extract_text"
    description = "Navigate to a URL and extract visible text content from the page"
    risk_level = "low"
    timeout_seconds = 30
    required_permissions = ["browser.read"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        url = context.get("url") or context.get("target_url", "")
        selector = context.get("selector", "body")
        if not url:
            return {"success": False, "error": "No URL provided", "output": None}
        if dry_run:
            return {"success": True, "output": {"text": "dry-run extracted text", "url": url}}

        sync_playwright = _get_playwright()
        if not sync_playwright:
            return {"success": False, "error": "playwright not installed", "output": None}

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=self.timeout_seconds * 1000)
                text = page.locator(selector).inner_text()
                browser.close()
            return {"success": True, "output": {"text": text[:4000], "url": url}}
        except Exception as e:
            return {"success": False, "error": str(e), "output": None}

class BrowserFillFormTool(BaseTool):
    name = "browser_fill_form"
    description = "Fill a form field on a page identified by CSS selector"
    risk_level = "medium"
    timeout_seconds = 30
    required_permissions = ["browser.write"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        url = context.get("url", "")
        selector = context.get("selector", "")
        value = context.get("value", "")
        if not selector or not value:
            return {"success": False, "error": "selector and value required", "output": None}
        if dry_run:
            return {"success": True, "output": {"filled": selector, "value": value[:20], "dry_run": True}}

        sync_playwright = _get_playwright()
        if not sync_playwright:
            return {"success": False, "error": "playwright not installed", "output": None}

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                if url:
                    page.goto(url, timeout=self.timeout_seconds * 1000)
                page.fill(selector, value)
                browser.close()
            return {"success": True, "output": {"filled": selector, "value_length": len(value)}}
        except Exception as e:
            return {"success": False, "error": str(e), "output": None}

class BrowserClickTool(BaseTool):
    name = "browser_click"
    description = "Click an element on a page identified by CSS selector or text"
    risk_level = "medium"
    timeout_seconds = 30
    required_permissions = ["browser.write"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        url = context.get("url", "")
        selector = context.get("selector", "")
        text = context.get("text", "")
        if not selector and not text:
            return {"success": False, "error": "selector or text required", "output": None}
        if dry_run:
            return {"success": True, "output": {"clicked": selector or text, "dry_run": True}}

        sync_playwright = _get_playwright()
        if not sync_playwright:
            return {"success": False, "error": "playwright not installed", "output": None}

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                if url:
                    page.goto(url, timeout=self.timeout_seconds * 1000)
                if selector:
                    page.click(selector)
                else:
                    page.get_by_text(text).click()
                browser.close()
            return {"success": True, "output": {"clicked": selector or text}}
        except Exception as e:
            return {"success": False, "error": str(e), "output": None}

class BrowserScreenshotTool(BaseTool):
    name = "browser_screenshot"
    description = "Capture a screenshot of a URL for audit logging"
    risk_level = "low"
    timeout_seconds = 30
    required_permissions = ["browser.read", "filesystem.write"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        import os
        from pathlib import Path
        url = context.get("url", "")
        output_path = context.get("screenshot_path", str(Path.home() / ".momentum" / "screenshots" / f"screenshot_{int(time.time())}.png"))
        if dry_run:
            return {"success": True, "output": {"path": output_path, "dry_run": True}}

        sync_playwright = _get_playwright()
        if not sync_playwright:
            return {"success": False, "error": "playwright not installed", "output": None}

        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                if url:
                    page.goto(url, timeout=self.timeout_seconds * 1000)
                page.screenshot(path=output_path)
                browser.close()
            return {"success": True, "output": {"path": output_path, "url": url}}
        except Exception as e:
            return {"success": False, "error": str(e), "output": None}

BROWSER_TOOLS = [
    BrowserNavigateTool(),
    BrowserExtractTextTool(),
    BrowserFillFormTool(),
    BrowserClickTool(),
    BrowserScreenshotTool(),
]
