from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from db.teams import TestTeamDistributor
from db.users import activate_all_users, deactivate_all_users
import json
import asyncio
import os


templates = Jinja2Templates(directory="web/templates")
router = APIRouter()
LOG_FILE = "app.log"

import re
from collections import Counter


def format_distribution_structured(lines):
    teams = []
    total_conflicts_counter = Counter()
    total_conflicts_count = 0

    current_team = None
    members = []
    conflict_tags_counter = Counter()

    for line in lines:
        line = line.strip()
        if line.startswith("🟢 Команда"):
            # Если есть текущая команда, сохраним её
            if current_team is not None:
                teams.append({
                    "team_num": current_team["team_num"],
                    "members_count": current_team["members_count"],
                    "conflict_count": current_team["conflict_count"],
                    "members": members,
                    "conflict_tags_counter": dict(conflict_tags_counter),
                })
                total_conflicts_counter.update(conflict_tags_counter)
                total_conflicts_count += current_team["conflict_count"]

            # Парсим заголовок команды
            m = re.match(r"🟢 Команда #(\d+) \((\d+) участников, (\d+) с конфликтами\)", line)
            if not m:
                continue

            current_team = {
                "team_num": int(m.group(1)),
                "members_count": int(m.group(2)),
                "conflict_count": int(m.group(3)),
            }
            members = []
            conflict_tags_counter = Counter()

        elif current_team is not None and line and not line.startswith("📊"):
            # Парсим участников — формат:
            # "  428323022 | Оводенко Данил | Backend, Python, ... | OK"
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 4:
                continue
            uid, name, tags, status = parts
            conflict_tags = []
            if status.startswith("Конфликт:"):
                conflict_tags = [tag.strip() for tag in status[len("Конфликт:"):].split(",")]
                for tag in conflict_tags:
                    conflict_tags_counter[tag] += 1
            members.append({
                "id": uid,
                "name": name,
                "tags": tags,
                "status": status,
                "conflicts": conflict_tags,
            })

        elif line.startswith("📊 Общая статистика конфликтов:"):
            # Это строка с общей статистикой — её можно просто пропустить,
            # или сохранить, если нужна
            pass

    # Добавим последнюю команду
    if current_team is not None:
        teams.append({
            "team_num": current_team["team_num"],
            "members_count": current_team["members_count"],
            "conflict_count": current_team["conflict_count"],
            "members": members,
            "conflict_tags_counter": dict(conflict_tags_counter),
        })
        total_conflicts_counter.update(conflict_tags_counter)
        total_conflicts_count += current_team["conflict_count"]

    top3 = total_conflicts_counter.most_common(3)
    most_conflict_tag = total_conflicts_counter.most_common(1)[0][0] if total_conflicts_counter else "нет"

    overall_stats = {
        "total_conflicts": total_conflicts_count,
        "top3_conflicts": top3,
        "most_conflict_tag": most_conflict_tag,
    }

    return {"teams": teams, "overall_stats": overall_stats}


async def run_test_distribution():
    push = []
    with TestTeamDistributor() as distributor:
        distributor.num_teams = 5
        result = distributor.simulate_distribution(max_team_size=6)
        for line in result:
            push.append(line)

    structured_data = format_distribution_structured(push)
    output_json = json.dumps(structured_data, ensure_ascii=False, indent=2)
    return output_json

async def run_main_distribution():
    return "Результат основного распределения"

async def activate_all():
    await activate_all_users()
    return "Активированы все пользователи с портфолио"

async def deactivate_all():
    await deactivate_all_users()
    return "Деактивированы все пользователи"

# Словарь команд: ключ — команда, значение — функция
ADMIN_COMMANDS = {
    "test_distribution": run_test_distribution,
    "main_distribution": run_main_distribution,
    "activate_all": activate_all,
    "deactivate_all": deactivate_all,
}

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                logs = lines[-100:] if len(lines) > 100 else lines
        except Exception as e:
            logs = [f"Ошибка при чтении лога: {e}\n"]
    else:
        logs = ["Лог файл не найден.\n"]

    return templates.TemplateResponse("index.html", {
        "request": request,
        "logs": "".join(logs)
    })

@router.post("/run_command", response_class=JSONResponse)
async def run_command_endpoint(command: str = Form(...)):
    if command not in ADMIN_COMMANDS:
        return JSONResponse({"error": "Недопустимая команда"}, status_code=400)

    try:
        # Вызываем функцию из словаря, которая должна вернуть строку
        output = await ADMIN_COMMANDS[command]()
    except Exception as e:
        return JSONResponse({"error": f"Ошибка при выполнении команды: {e}"}, status_code=500)

    return {"output": output}

@router.get("/test-team", response_class=HTMLResponse)
async def test_teams(request: Request):
    result_json = await run_test_distribution()
    output = json.loads(result_json)
    return templates.TemplateResponse("test_teams.html", {
        "request": request,
        "teams": output['teams'],
        "overall_stats": output['overall_stats']
    })