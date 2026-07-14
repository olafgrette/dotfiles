---
name: gemini-image-read
description: Use this skill whenever you need to read, identify, or extract content from an image file, scanned document, or any file whose contents can't be determined from its name or extension alone. This includes JPG, PNG, GIF, PDF scans, TIFF, HEIC, and similar files. Trigger this skill proactively any time you encounter an image you need to understand — don't try to read binary image data directly. If you're unsure whether something is an image, use this skill rather than attempting to read the file with standard tools.
---

# Reading Image Files with agy

When you encounter an image or scanned document that needs to be identified or read, use the `agy` command line tool. If `agy` is unavailable (e.g. on remote hosts where it is not installed), fall back to `gemini`.

## Check availability

Verify if `agy` is installed before using it:
```bash
if command -v agy &>/dev/null; then
    # use agy
else
    # use gemini
fi
```

## Command syntax

If `agy` is available, run:
```bash
agy --print "What does this image show? Describe it briefly. @/absolute/path/to/file.jpg"
```

If `agy` is unavailable, fall back to `gemini`:
```bash
gemini -p "What does this image show? Describe it briefly. @/absolute/path/to/file.jpg"
```

Key points:
- Always use the **absolute path** to the file
- Prefix the path with `@` directly in the prompt string (no space between `@` and the path)
- For `agy`, use `--print` for non-interactive operation
- For `gemini`, the prompt and file reference are a single string passed to `-p`

## Tailoring the prompt

Match the prompt to what you actually need:

- **Identifying an unknown image**:
  - `agy`: `agy --print "What is in this image? Describe it in one sentence. @/path/to/file.jpg"`
  - `gemini` fallback: `gemini -p "What is in this image? Describe it in one sentence. @/path/to/file.jpg"`
- **Reading a scanned document**:
  - `agy`: `agy --print "What does this image show? What does the document say? Summarize it briefly. @/path/to/scan.pdf"`
  - `gemini` fallback: `gemini -p "What does this image show? What does the document say? Summarize it briefly. @/path/to/scan.pdf"`
- **Batch identification**: Run one command call per file — don't pass multiple `@` references in one call
