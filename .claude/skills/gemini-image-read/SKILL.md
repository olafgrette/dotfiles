---
name: gemini-image-read
description: Use this skill whenever you need to read, identify, or extract content from an image file, scanned document, or any file whose contents can't be determined from its name or extension alone. This includes JPG, PNG, GIF, PDF scans, TIFF, HEIC, and similar files. Trigger this skill proactively any time you encounter an image you need to understand — don't try to read binary image data directly. If you're unsure whether something is an image, use this skill rather than attempting to read the file with standard tools.
---

# Reading Image Files with Gemini CLI

When you encounter an image or scanned document that needs to be identified or read, use the Gemini CLI — it has strong multimodal capabilities and can be called headlessly.

## Command syntax

```bash
gemini -p "What does this image show? Describe it briefly. @/absolute/path/to/file.jpg"
```

Key points:
- Always use the **absolute path** to the file
- Prefix the path with `@` directly in the prompt string (no space between `@` and the path)
- The prompt and file reference are a single string passed to `-p`

## Tailoring the prompt

Match the prompt to what you actually need:

- **Identifying an unknown image**: `"What is in this image? Describe it in one sentence. @/path/to/file.jpg"`
- **Reading a scanned document**: `"What does this image show? What does the document say? Summarize it briefly. @/path/to/scan.pdf"`
- **Batch identification**: Run one `gemini` call per file — don't pass multiple `@` references in one call
