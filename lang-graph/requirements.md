# Training Project Requirements — Grooming Agent Case Study

## Purpose
We are building a simplified agent for a grooming business.
It should talk to customers on Discord, capture their info, give service details and prices, and book appointments into Google Calendar.
All data about leads, pets, services, and bookings will live in Google Sheets (Sheet with dummy data).

## Flow (step by step)
1. **User sends a message on Discord**
2. **Agent receives the request**
   * Starts a new lead record in the Leads sheet with `status = initiated`.
3. **Agent qualifies the lead**
   * Collects user’s basic details (name, phone) and pet details (breed, weight, age, coat).
   * Updates lead `status = qualified`.
4. **Agent provides info**
   * Reads from the Services sheet to show correct services, durations, and prices.
5. **Agent asks to book**
   * If yes, checks available time slots from Google Calendar.
   * Books appointment $\rightarrow$ writes to Appointments sheet and creates Calendar event.
   * Updates lead `status = booked`.
6. **Agent handles generic/info queries**
   * Hours, location, contact info from BrandConfig sheet.
7. **Agent follows up**
   * If the lead stalls before booking, sends a reminder message.

## Functional Requirements
* Agent must always update lead status at each stage.
* Agent must always get service info from the Services sheet (not hardcoded).
* Appointment is only valid if both Appointments sheet and Google Calendar confirm it.
* If an error occurs (e.g., slot conflict, missing info), the agent must explain and suggest alternatives.
* Agent must follow a predictable 7-step flow (FSM control).
* Follow-up messages must be scheduled if booking doesn’t happen.

## Acceptance Criteria
* A customer can start a Discord chat and reach a confirmed booking.
* Quotes shown match the Services sheet exactly.
* Bookings appear in both Google Calendar and Appointments sheet.
* Lead status transitions correctly: `initiated` $\rightarrow$ `qualified` $\rightarrow$ `booked`.
* Business info questions are answered from BrandConfig.
* At least one reminder is sent for unbooked leads.

## Test Cases

### Case 1 – Standard Booking
* **Customer:** “Hi, I need grooming for my dog Bella.”
* **Expected:** New lead record $\rightarrow$ collect details $\rightarrow$ show service options $\rightarrow$ show times $\rightarrow$ confirm booking $\rightarrow$ update status to booked.

### Case 2 – Missing Info
* **Customer:** “I need grooming.”
* **Expected:** Bot asks again until breed, weight, age, and coat are provided $\rightarrow$ continues booking flow.

### Case 3 – Service Not Found
* **Customer:** Pet breed/weight not in Services sheet.
* **Expected:** Suggest closest available service/package $\rightarrow$ continue flow.

### Case 4 – Customer Objection
* **Customer:** “That’s too expensive.”
* **Expected:** Bot uses objection handling snippet (value explanation, alternative option, or add-on).

### Case 5 – No Booking Yet
* **Customer:** “I’ll think about it.”
* **Expected:** Lead status = `qualified` $\rightarrow$ bot schedules a follow-up DM within 24–48h.

## Exercise Instructions
You will implement the above workflow in four different ways:
1. **Prompt-based** — Build the flow using only prompt engineering. When the bot “acts,” outputs in a structured format (simulate action).
2. **LangGraph** — Implement the workflow as a LangGraph graph.
3. **MCP Server** — Implement as an MCP server with clearly defined endpoints for lead, services, and booking.
4. **Agent-to-Agent (A2A)** — Split tasks across multiple smaller agents that coordinate with each other.

> **Important Note:** All the test cases should be tested using Evals. All four versions must pass the five test cases above.