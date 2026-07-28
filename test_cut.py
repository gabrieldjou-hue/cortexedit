"""Smoke test for the Cut Editor module."""
import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    page.goto("http://127.0.0.1:8016/")
    page.wait_for_load_state("networkidle")
    time.sleep(1)

    # 1. Go to Cut tab
    page.click('[data-tab="cuts"]')
    time.sleep(0.5)

    # 2. Upload file
    page.set_input_files("#cutFileInput",
        r"C:\Users\usuario\.gemini\antigravity\scratch\ai-video-editor-platform\test_whisper_input.mp4")
    time.sleep(0.5)

    # 3. Click Analyze
    page.click("#btnAnalyzeCuts")

    # Wait for suggestions panel to appear
    for _ in range(60):
        time.sleep(0.5)
        visible = page.locator("#cutStepSuggestions").is_visible()
        if visible:
            break
    print(f"Suggestions visible: {visible}")

    suggestions = page.query_selector_all(".cut-suggestion-card")
    print(f"Suggestions generated: {len(suggestions)}")
    page.screenshot(
        path=r"C:\Users\usuario\.gemini\antigravity\scratch\ai-video-editor-platform\screenshot_cut_suggestions.png",
        full_page=True)

    # 4. Click Cut Selected
    if suggestions:
        page.click("#btnCutSelected")
        # Wait for clips panel
        for _ in range(60):
            time.sleep(0.5)
            clips_visible = page.locator("#cutStepClips").is_visible()
            if clips_visible:
                break
        print(f"Clips panel visible: {clips_visible}")
        clips = page.query_selector_all(".cut-clip-card")
        print(f"Clips generated: {len(clips)}")
        page.screenshot(
            path=r"C:\Users\usuario\.gemini\antigravity\scratch\ai-video-editor-platform\screenshot_cut_clips.png",
            full_page=True)

    if errors:
        print(f"JS ERRORS: {errors}")
    else:
        print("No JS errors")

    browser.close()
    print("All OK")
