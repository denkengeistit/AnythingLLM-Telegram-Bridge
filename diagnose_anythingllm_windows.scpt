#!/usr/bin/osascript

-- Diagnostic script to find AnythingLLM window names
tell application "System Events"
    set anythingLLMProcess to process "AnythingLLM"
    
    -- Get all windows
    set windowList to every window of anythingLLMProcess
    
    log "Found " & (count of windowList) & " windows in AnythingLLM:"
    
    repeat with i from 1 to count of windowList
        set currentWindow to item i of windowList
        set windowName to name of currentWindow
        log "Window " & i & ": " & windowName
        
        -- Also check if it has any UI elements that might indicate it's the assistant
        try
            set uiElements to every UI element of currentWindow
            log "  - Has " & (count of uiElements) & " UI elements"
        on error
            log "  - Could not access UI elements"
        end try
    end repeat
    
    -- Try to find windows with "Assistant" in the name
    log ""
    log "Looking for windows containing 'Assistant':"
    repeat with currentWindow in windowList
        set windowName to name of currentWindow
        if windowName contains "Assistant" then
            log "Found Assistant window: " & windowName
        end if
    end repeat
    
    -- Try to find the mini assistant specifically
    log ""
    log "Looking for mini assistant or chat interface:"
    repeat with currentWindow in windowList
        set windowName to name of currentWindow
        if windowName contains "mini" or windowName contains "chat" or windowName contains "AI" then
            log "Potential chat/assistant window: " & windowName
        end if
    end repeat
end tell