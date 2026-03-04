# Media Support - Photo Upload Feature

## Overview

The AnythingLLM Telegram Bridge now supports photo uploads! Send any image through Telegram and it will be automatically uploaded to your configured AnythingLLM workspace for analysis.

## Features

✅ **Photo Upload**: Send photos from Telegram → automatically uploaded to AnythingLLM workspace  
✅ **Image Metadata**: Automatically extracts format, dimensions, and file size  
✅ **Temp File Management**: Downloads, processes, uploads, then cleans up temporary files  
✅ **Error Handling**: Robust error handling with user-friendly messages  
✅ **Multiple Formats**: Supports PNG, JPEG, GIF, WebP, and other Pillow-supported formats  

## Usage

1. **Start the bridge** with your AnythingLLM credentials configured
2. **Send a photo** in Telegram (any format)
3. **Get confirmation** that the photo was uploaded with metadata
4. **Chat with your agent** about the uploaded image

### Example Conversation

```
👤 User: [Sends a screenshot of a login page]
🤖 Bridge: [Image: PNG 1920x1080, 245KB - uploaded to workspace]
👤 User: What UI improvements could be made to this login screen?
🤖 Agent: Looking at your uploaded screenshot, I can see several potential improvements for the login screen...
```

## Technical Details

### Photo Processing Pipeline

1. **Download**: Photo downloaded from Telegram to temp directory
2. **Process**: Extract metadata (format, dimensions, file size) using Pillow
3. **Upload**: Send to AnythingLLM workspace via multipart form upload
4. **Cleanup**: Remove temporary file
5. **Respond**: Send confirmation with image details

### Supported Formats

- PNG, JPEG, GIF, WebP, BMP, TIFF
- Any format supported by Pillow library

### File Size Limits

- Telegram limits: Up to 10MB for photos sent as photos
- Telegram limits: Up to 50MB for photos sent as documents
- AnythingLLM limits: Depends on your instance configuration

## Error Handling

The bridge handles various error scenarios gracefully:

- **Network errors**: Retry logic for upload failures
- **Format errors**: Fallback descriptions if image processing fails
- **Storage errors**: Clear error messages for upload issues
- **Cleanup errors**: Silent cleanup with warnings in logs

## Configuration

No additional configuration needed beyond the standard bridge setup:

```bash
export TELEGRAM_BOT_TOKEN="your-bot-token"
export ANYTHINGLLM_API_KEY="your-api-key"
export ANYTHINGLLM_BASE_URL="http://localhost:3001"
export ANYTHINGLLM_WORKSPACE="your-workspace-slug"
```

## Testing

Run the included test to verify photo processing:

```bash
python3 test_media.py
```

## Next Features (Planned)

🚧 **Audio Support**: Voice messages and audio files  
🚧 **Document Support**: Enhanced document processing  
🚧 **Batch Upload**: Multiple files in one message  
🚧 **Image Analysis**: Built-in image description before upload  

## Troubleshooting

### "Photo upload failed" errors
- Check your AnythingLLM API key and workspace permissions
- Verify the workspace exists and accepts file uploads
- Check AnythingLLM storage space and limits

### "Media processing error" messages
- Ensure Pillow is installed: `pip install Pillow>=10.0.0`
- Check that the image format is supported
- Verify temporary directory permissions

### Performance tips
- Large images are automatically handled but may take longer
- Consider resizing very large images before sending
- The bridge processes one image at a time for reliability