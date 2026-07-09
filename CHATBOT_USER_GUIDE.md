# Vinci Automation Chatbot User Guide

## Overview

The Vinci Automation chatbot is an AI-powered admin assistant that helps you manage tutoring operations through natural language conversations. It serves as your intelligent interface to the database, allowing you to query information, modify data, and perform administrative tasks without needing to navigate complex interfaces.

## Accessing the Chatbot

The chatbot is accessible from any page in the Vinci Automation system:

1. **Expand the Assistant Panel**: Click the "Assistant" button on the right side of the screen
2. **Two Main Tabs**:
   - **Chat Tab**: Natural language conversations with the AI
   - **Data Tab**: Quick input forms and data export tools

## Chat Tab Features

### Natural Language Queries

The chatbot can answer questions about your tutoring operations in plain English, Cantonese, or Mandarin:

#### Common Query Examples:

**Schedule & Lessons:**
- "Show me today's schedule"
- "What lessons are on tomorrow?"
- "List all unassigned lessons"
- "Show urgent lessons within a week"
- "What's happening next week?"
- "Give me a summary of the current schedule"

**Database Overview:**
- "How many schools do we have?"
- "Count all teachers in the system"
- "Database summary"
- "Total number of lessons"

**Specific Information:**
- "Show me all IGCSE Physics lessons"
- "What lessons are at St. Mary's School?"
- "Who is teaching Advanced Robotics?"

### Multi-Language Support

The chatbot understands and responds in:
- **English**: Standard queries and responses
- **Cantonese**: Traditional Chinese characters and colloquialisms
- **Mandarin**: Simplified Chinese characters

**Cantonese Examples:**
- "今日有咩課？" (What lessons are today?)
- "顯示所有未分配的課程" (Show all unassigned lessons)
- "星期五有幾多堂？" (How many lessons on Friday?)

### Preset Quick Actions

At the top of the chat panel, you'll find preset buttons for common operations:

- **"Show unassigned lessons"**: Lists all lessons without assigned tutors
- **"Today's schedule"**: Shows all lessons scheduled for today
- **"Urgent (within a week)"**: Displays lessons needing attention within 7 days
- **"Summarise the schedule"**: Provides an overview of current schedule status
- **"Export lessons to Excel"**: Downloads all lessons as an Excel file

### Structured Commands

For precise data modifications, use the structured command system by clicking "▼ Commands":

#### 1. Reschedule Command
Change a lesson's date and/or time.

**Fields:**
- Lesson ID (required): e.g., L-2026-010
- New date: YYYY-MM-DD format
- New time: HH:MM format

**Example:**
```
Reschedule lesson L-2026-010 to 2026-07-15 at 16:00
```

#### 2. Update Command
Modify any lesson fields including status, course, notes, time, etc.

**Fields:**
- Lesson ID (required)
- Date, start/end time
- Course name
- Status (Cancelled, Completed, Rescheduled, etc.)
- Role (Tutor or Teaching Assistant)
- Max tutors
- Notes
- Material link

**Examples:**
```
Update lesson L-2026-010: status=Cancelled
Update lesson L-2026-010: notes=Parent requested afternoon
Update lesson L-2026-010: start_time=16:00, end_time=17:30
```

#### 3. Create Command
Create a new lesson with specified details.

**Fields:**
- School name
- Course name  
- Date
- Start time
- End time

**Example:**
```
Create a IGCSE Physics lesson at St. Mary's School on 2026-07-20 at 14:30-16:00
```

#### 4. Delete Command
Remove a lesson from the system.

**Fields:**
- Lesson ID (required)

**Example:**
```
Delete lesson L-2026-010
```

### AI-Powered Action Suggestions

When you ask the chatbot to modify data, it will:

1. **Understand your intent** using natural language processing
2. **Explain what it will do** before taking action
3. **Generate an ACTION block** with the specific operation
4. **Ask for confirmation** before executing

**Example Conversation:**

```
You: Move the IGCSE Physics lesson on July 10 to 16:00

Assistant: I can reschedule lesson L-2026-010 (IGCSE Physics) from July 10 14:00 to July 10 16:00. Shall I proceed?

ACTION:{"operation":"reschedule","params":{"lesson_id":"L-2026-010","start_time":"16:00"}}

[You click "Yes, proceed"]

Assistant: ✅ Done. Lesson L-2026-010 updated.
```

### Smart Context Awareness

The chatbot is grounded with live database data, including:

- **Current date and day** for relative time references
- **Course catalog** with all available courses
- **School catalog** with all registered schools  
- **Unassigned lessons** needing tutor assignment
- **Urgent lessons** within the upcoming week
- **Upcoming schedule** for context-aware responses

**Relative Date Examples:**
- "Show me lessons for tomorrow"
- "What's scheduled for next Monday?"
- "Any lessons this afternoon?"

### Intelligent Course & School Handling

The chatbot intelligently handles course and school references:

**Non-existent Course:**
```
You: Create a lesson for Advanced Rocketry at St. Mary's on 24/2 3:10-4:10

Assistant: The course "Advanced Rocketry" doesn't exist in our system. Would you like me to create it first?
```

**Non-existent School:**
```
You: Create a lesson for ICT Python at St. Mary's School on 24/2

Assistant: The school "St. Mary's School" doesn't exist in our system. Would you like me to create it first?
```

### Date/Time Format Handling

The chatbot understands various date/time formats:

**Standard Formats:**
- YYYY-MM-DD (2026-07-15)
- DD/MM/YYYY (15/07/2026)
- HH:MM time format (14:30)

**Cantonese Traditional Time:**
- "三點" = 3:00
- "三點半" = 3:30  
- "三點九" = 3:45

**Relative References:**
- "今日/聽日/後日" = today/tomorrow/day-after-tomorrow
- "上晝/下晝/朝早/晏晝/夜晚" = am/pm/morning/afternoon/evening

### Conversation History

The chatbot maintains your conversation history:

- **Auto-saved**: Conversations persist across sessions
- **Clear history**: Option to reset conversation
- **Context-aware**: Uses previous messages for better understanding
- **Maximum storage**: Keeps last 60 messages

## Data Tab Features

### Quick Input Forms

The Data tab provides structured forms for rapid data entry:

#### Lesson Form
Two modes available:

**Create Only Mode:**
- Saves lesson to database without sending notifications
- Useful for planning and scheduling
- No WhatsApp messages sent

**Create & Announce Mode:**
- Creates lesson AND messages suitable tutors
- Uses AI or rule-based tutor selection
- Sends WhatsApp notifications automatically
- Shows which tutors were messaged

**Lesson Form Fields:**
- Course selection (from existing courses)
- School selection (from existing schools)
- Date and time fields
- Number of tutors needed
- Lesson income (HKD)
- Material link (optional)

#### Teacher Form
Quickly add new teachers:
- Full name (required)
- WhatsApp number
- Email address

#### Course Form
Add new courses:
- Course name (required)
- Course topic (optional)

#### School Form
Add new schools:
- School name (required)

### Excel Export

Export any dataset as Excel files with one click:

**Available Datasets:**
- **lessons**: All lessons in the system
- **unassigned**: Lessons without tutor assignments
- **urgent**: Lessons needing attention within a week
- **teachers**: All teacher records
- **courses**: All course information
- **schools**: All school data

**How to Export:**
1. Switch to Data tab
2. Find "Export to Excel" section
3. Click the desired dataset button
4. Excel file downloads automatically

## Advanced Features

### Offline Fallback

If the AI language model is unavailable, the chatbot automatically falls back to deterministic database queries:

- **Still operational**: Can answer common questions
- **Limited functionality**: Cannot process complex natural language
- **Clear messaging**: Informs you when operating in fallback mode

**Fallback-capable queries:**
- "Show unassigned lessons"
- "Today's schedule" 
- "Urgent within a week"
- "Database summary"
- "How many [entity]"

### Confirmation Workflow

All data-modifying actions require confirmation:

1. **Assistant proposes action** with explanation
2. **ACTION block displayed** with JSON details
3. **User confirmation required** via "Yes, proceed" button
4. **Execution feedback** shows success or failure
5. **Option to cancel** at any time

### Error Handling

The chatbot handles errors gracefully:

- **Backend unreachable**: Friendly error message with retry suggestion
- **Invalid data**: Clear error indicating what went wrong
- **Missing required fields**: Prompts for needed information
- **Action failures**: Detailed error messages for troubleshooting

## Best Practices

### Effective Query Formulation

**Be Specific:**
- ✅ "Show unassigned IGCSE Physics lessons for this week"
- ❌ "Show lessons"

**Use Complete Sentences:**
- ✅ "What lessons are scheduled at St. Mary's School tomorrow?"
- ❌ "St. Mary's tomorrow"

**Include Context:**
- ✅ "Create a new IGCSE Physics lesson at St. Mary's for next Tuesday at 14:30"
- ❌ "Create lesson next Tuesday"

### Data Modification Safety

**Always Verify:**
- Check the ACTION block details before confirming
- Ensure lesson IDs are correct
- Verify dates and times are accurate

**Use Structured Commands:**
- For complex updates, use the Commands interface
- Fill in all relevant fields for accuracy
- Review the generated natural language before sending

**Test with Non-Critical Data:**
- Try commands with test data first
- Verify the outcome before bulk operations
- Keep conversation history for reference

### Multi-Lesson Entry

For entering multiple lessons at once, use the **Multi-Lesson Entry** feature from the Schedule page instead of the chatbot. This is more efficient for batch operations.

## Troubleshooting

### Chatbot Not Responding

**Possible Causes:**
- Backend server is down
- Internet connectivity issues
- LLM provider unreachable

**Solutions:**
- Check if other features are working
- Try the Data tab for offline operations
- Contact technical support if issue persists

### Incorrect Query Results

**Possible Causes:**
- Ambiguous question phrasing
- Outdated database information
- Language translation issues

**Solutions:**
- Rephrase your question more specifically
- Try using English if using Chinese
- Check the Schedule page for verification

### Action Confirmation Issues

**Possible Causes:**
- Invalid lesson ID format
- Missing required fields
- Permission restrictions

**Solutions:**
- Verify lesson ID from Schedule page
- Ensure all required fields are filled
- Check you have admin permissions

## Tips & Tricks

### Keyboard Shortcuts
- **Enter**: Send message
- **Shift + Enter**: New line in message input

### Quick Navigation
- **Click "Assistant"**: Expand/collapse the panel
- **Tab switching**: Quickly move between Chat and Data tabs
- **Clear history**: Reset conversation when starting new tasks

### Efficiency Tips
- Use preset buttons for common queries
- Save complex queries as conversation bookmarks
- Use Excel export for data analysis
- Leverage structured commands for precision

### Integration with Other Features

**Schedule Page Integration:**
- Chatbot actions automatically refresh the schedule
- Lesson details from chatbot link to schedule views
- Unassigned lessons from chatbot appear in dashboard

**Dashboard Integration:**
- Chatbot can query dashboard data
- Actions taken in chatbot reflect in dashboard
- Export functionality works across all views

## Technical Information

### How It Works

**LLM Integration:**
- Uses OpenAI-compatible providers (Groq, Ollama, etc.)
- Grounded with live database snapshots
- JSON mode for structured action generation

**Database Connection:**
- Direct Supabase integration
- Real-time data access
- Transaction-based modifications

**Language Processing:**
- Cantonese/Mandarin to English translation
- Preserves original language in responses
- Context-aware translation

### Privacy & Security

**Data Handling:**
- All queries processed server-side
- No external data storage beyond LLM provider
- Conversation history stored locally in browser

**Access Control:**
- Admin authentication required
- Role-based permissions enforced
- Action confirmation prevents unauthorized changes

## Support

For technical issues or questions about the chatbot:

1. Check this user guide for common solutions
2. Review the GitHub repository for known issues
3. Contact the development team for advanced support

---

**Version:** 1.0  
**Last Updated:** July 2026  
**For:** Vinci Automation System