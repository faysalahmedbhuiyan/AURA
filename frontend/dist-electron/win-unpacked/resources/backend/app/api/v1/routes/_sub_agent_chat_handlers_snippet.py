async def _handle_sub_agent_list(db) -> str:
    from app.agents_v2.sub_agent_factory import sub_agent_factory

    agents = await sub_agent_factory.list_sub_agents(db)
    if not agents:
        return "এখনো কোনো sub-agent তৈরি হয়নি। 'create sub agent: <task>' লিখে একটা বানাও।"

    lines = ["তোমার sub-agents:"]
    for a in agents:
        lines.append(f"• **{a['name']}** — {a['task_description']} ({a['knowledge_count']} things taught)")
    return "\n".join(lines)


async def _handle_sub_agent_create(message: str, db) -> str:
    from app.agents_v2.sub_agent_factory import sub_agent_factory

    task_description = message.split(":", 1)[1].strip() if ":" in message else ""
    if not task_description:
        return "কী কাজের জন্য sub-agent বানাতে চাও? যেমন: 'create sub agent: writing Python code'"

    result = await sub_agent_factory.create_sub_agent(db, task_description)
    return (
        f"✅ Sub-agent **{result['name']}** তৈরি হয়েছে, কাজ: {task_description}\n\n"
        f"এখন শেখাতে পারো: 'teach sub agent {result['name']}: <কিছু তথ্য>'\n"
        f"জিজ্ঞেস করতে পারো: 'ask sub agent {result['name']}: <প্রশ্ন>'"
    )


async def _handle_sub_agent_teach(message: str, db) -> str:
    from app.agents_v2.sub_agent_factory import sub_agent_factory

    # "teach sub agent <name>: <content>"  or  "sub agent <name> shikhao: <content>"
    m = re.match(r'^(?:teach\s+sub[- ]?agent|sub[- ]?agent)\s+(\S+)', message, re.IGNORECASE)
    name = m.group(1) if m else ""
    content = message.split(":", 1)[1].strip() if ":" in message else ""

    if not name or not content:
        return "সঠিক format: 'teach sub agent <name>: <শেখানোর তথ্য>'"

    result = await sub_agent_factory.teach(db, name, content)
    if not result.get("success"):
        return f"❌ {result.get('error')}"
    return f"✅ **{name}**-কে শেখানো হয়েছে।"


async def _handle_sub_agent_ask(message: str, db) -> str:
    from app.agents_v2.sub_agent_factory import sub_agent_factory

    m = re.match(r'^(?:ask\s+sub[- ]?agent|sub[- ]?agent)\s+(\S+)', message, re.IGNORECASE)
    name = m.group(1) if m else ""
    question = message.split(":", 1)[1].strip() if ":" in message else ""

    if not name or not question:
        return "সঠিক format: 'ask sub agent <name>: <প্রশ্ন>'"

    result = await sub_agent_factory.ask(db, name, question)
    if not result.get("success"):
        return f"❌ {result.get('error')}"
    return f"🤖 **{name}**:\n\n{result['answer']}"
