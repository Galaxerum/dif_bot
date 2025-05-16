import sqlite3
from typing import List, Dict, Any, Set
from pathlib import Path
import json

DB_PATH = Path(__file__).parent.parent / "main.db"


class TeamDistributor:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.color_limits = {}  # color -> max number of teams with that color

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

    def setup_colors(self, color_limits: Dict[str, int]):
        """Инициализирует команды и лимиты по цветам."""
        self.color_limits = color_limits
        with self.conn:
            self.conn.execute("DELETE FROM teams")
            for color, limit in color_limits.items():
                if limit > 0:  # Создаём команды только для цветов с положительным лимитом
                    for _ in range(limit):
                        self.conn.execute("INSERT INTO teams (colors) VALUES (?)", (color,))

    def get_users_to_distribute(self) -> List[Dict]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT u.user_id, u.username, u.portfolio, 
                   (SELECT GROUP_CONCAT(t.tag) 
                    FROM tags t 
                    WHERE t.user_id = u.user_id) as tags
            FROM users u
            WHERE u.relevance = 1 AND u.team_id IS NULL
        """)
        return [
            {
                "user_id": row["user_id"],
                "username": row["username"],
                "portfolio": row["portfolio"],
                "tags": json.loads(row["tags"]) if row["tags"] else []
            }
            for row in cur.fetchall()
        ]

    def get_team_stats(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT t.id, t.colors, COUNT(u.user_id) as members
            FROM teams t
            LEFT JOIN users u ON t.id = u.team_id AND u.relevance = 1
            GROUP BY t.id
            ORDER BY members ASC
        """)
        return [
            {
                "id": row["id"],
                "color": row["colors"],
                "members": row["members"]
            }
            for row in cur.fetchall()
        ]

    def get_team_tags(self, team_id: int) -> Set[str]:
        """Возвращает множество тегов пользователей команды."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT t.tag FROM tags t
            JOIN users u ON t.user_id = u.user_id
            WHERE u.team_id = ? AND u.relevance = 1
        """, (team_id,))
        tags = {row["tag"] for row in cur.fetchall()}
        return tags

    def get_color_team_count(self, color: str) -> int:
        """Возвращает количество команд с заданным цветом."""
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM teams WHERE colors = ?", (color,))
        return cur.fetchone()[0]

    def distribute_users(self, max_team_size: int = 10):
        """Распределяет пользователей по командам с учетом их тегов и ограничений"""
        users = self.get_users_to_distribute()
        teams = self.get_team_stats()

        # Инициализация команд (только цвета с положительным лимитом)
        if not teams:
            with self.conn:
                for color, limit in self.color_limits.items():
                    if limit > 0:
                        for _ in range(limit):
                            self.conn.execute("INSERT INTO teams (colors) VALUES (?)", (color,))
            teams = self.get_team_stats()

        # Собираем теги для каждой команды
        team_tags = {team["id"]: set(self.get_team_tags(team["id"])) for team in teams}

        output = []

        for user in users:
            user_tags = set(user["tags"])
            best_team = None
            min_conflicts = float('inf')
            min_members = float('inf')

            # 1. Ищем команду без конфликтов (со свободными местами)
            for team in teams:
                if team["members"] < max_team_size and team_tags[team["id"]].isdisjoint(user_tags):
                    best_team = team
                    break

            # 2. Ищем команду с минимальными конфликтами (со свободными местами)
            if not best_team:
                for team in teams:
                    if team["members"] >= max_team_size:
                        continue

                    conflicts = len(team_tags[team["id"]].intersection(user_tags))
                    if conflicts < min_conflicts or (conflicts == min_conflicts and team["members"] < min_members):
                        best_team = team
                        min_conflicts = conflicts
                        min_members = team["members"]

            # 3. Если все команды переполнены, ищем любую с минимальными конфликтами
            if not best_team:
                # Фильтруем только команды с положительным лимитом цвета
                eligible_teams = [t for t in teams if self.color_limits.get(t["color"], 0) > 0]
                if eligible_teams:
                    best_team = min(
                        eligible_teams,
                        key=lambda x: (
                            len(team_tags[x["id"]].intersection(user_tags)),
                            x["members"]
                        )
                    )

            # 4. Если можно создать новую команду (по лимиту цвета)
            if not best_team or best_team["members"] >= max_team_size:
                # Находим цвет с наименьшим количеством команд (но в пределах лимита)
                color_counts = {}
                for team in teams:
                    color = team["color"]
                    if self.color_limits.get(color, 0) > 0:
                        color_counts[color] = color_counts.get(color, 0) + 1

                available_colors = [color for color, limit in self.color_limits.items()
                                    if limit > 0 and color_counts.get(color, 0) < limit]

                if available_colors:
                    color = min(available_colors, key=lambda c: color_counts.get(c, 0))
                    with self.conn:
                        self.conn.execute("INSERT INTO teams (colors) VALUES (?)", (color,))
                        new_team_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    new_team = {"id": new_team_id, "color": color, "members": 0}
                    teams.append(new_team)
                    team_tags[new_team_id] = set()
                    best_team = new_team

            if not best_team:
                output.append(f"{user['user_id']} | {user.get('username', '')} | ❌ Нет доступных команд")
                continue

            # Проверяем конфликты для логов
            status = []
            if best_team["members"] >= max_team_size:
                status.append("🟡 переполнение")
            if not team_tags[best_team["id"]].isdisjoint(user_tags):
                status.append("⚠️ конфликт тегов")
            if not status:
                status.append("✅ OK")

            # Обновляем данные в БД
            with self.conn:
                self.conn.execute(
                    "UPDATE users SET team_id = ? WHERE user_id = ?",
                    (best_team["id"], user["user_id"])
                )

            # Обновляем теги и счетчики
            team_tags[best_team["id"]].update(user_tags)
            best_team["members"] += 1

            # Формируем строку лога
            output.append(
                f"{user['user_id']} | {user.get('username', '')} | {user['tags']} | "
                f"команда #{best_team['id']} ({best_team['color']}) {' + '.join(status)}"
            )

        # Выводим все логи
        for line in output:
            print(line)

    def clear_all_teams(self):
        """Удаляет все команды и обнуляет team_id у всех пользователей"""
        with self.conn:
            self.conn.execute("DELETE FROM teams")
            self.conn.execute("UPDATE users SET team_id = NULL")



class TestTeamDistributor:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.color_limits: Dict[str, int] = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

    def setup_colors(self, color_limits: Dict[str, int]):
        """Сохраняем лимиты на количество команд по цветам (без записи в БД)"""
        self.color_limits = color_limits

    def get_users_to_distribute(self) -> List[Dict]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT u.user_id, u.username, u.portfolio, 
                   (SELECT GROUP_CONCAT(t.tag) 
                    FROM tags t 
                    WHERE t.user_id = u.user_id) as tags
            FROM users u
            WHERE u.relevance = 1 AND u.team_id IS NULL
        """)
        users = []
        for row in cur.fetchall():
            raw_tags = row["tags"]
            # raw_tags сейчас строка вида: '["Программист", "C++", "Программирование"]'
            if raw_tags:
                try:
                    tags = json.loads(raw_tags)
                except Exception:
                    # если парсинг не удался — пытаемся разбить через запятую и убрать кавычки
                    tags = [tag.strip().strip('"').strip("'") for tag in raw_tags.split(",")]
            else:
                tags = []
            users.append({
                "user_id": row["user_id"],
                "username": row["username"],
                "portfolio": row["portfolio"],
                "tags": tags,
            })
        return users

    def get_team_stats(self) -> List[Dict[str, Any]]:
        """Возвращает список команд с их цветом и числом участников"""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT t.id, t.colors, COUNT(u.user_id) as members
            FROM teams t
            LEFT JOIN users u ON t.id = u.team_id AND u.relevance = 1
            GROUP BY t.id
            ORDER BY members ASC
        """)
        return [
            {
                "id": row["id"],
                "color": row["colors"],
                "members": row["members"]
            }
            for row in cur.fetchall()
        ]

    def get_color_team_count(self, teams: List[Dict], color: str) -> int:
        """Подсчитывает количество команд данного цвета в списке"""
        return sum(1 for team in teams if team["color"] == color)

    def simulate_distribution(self, max_team_size: int = 10) -> List[str]:
        users = self.get_users_to_distribute()
        teams = self.get_team_stats()

        # Инициализация команд
        if not teams:
            teams = []
            team_id = 1
            for color, limit in self.color_limits.items():
                if limit > 0:
                    for _ in range(limit):
                        teams.append({
                            "id": team_id,
                            "color": color,
                            "members": 0,
                            "tags": set()
                        })
                        team_id += 1

        simulated_teams = [team.copy() for team in teams]
        for team in simulated_teams:
            team["tags"] = set()

        output = []

        for user in users:
            user_tags = set(user["tags"])
            best_team = None
            min_conflicts = float('inf')
            min_members = float('inf')

            # 1. Ищем команду без конфликтов (свободную)
            for team in simulated_teams:
                if team["members"] < max_team_size and team["tags"].isdisjoint(user_tags):
                    best_team = team
                    break

            # 2. Ищем команду с минимальными конфликтами (свободную)
            if not best_team:
                for team in simulated_teams:
                    if team["members"] >= max_team_size:
                        continue
                    conflicts = len(team["tags"].intersection(user_tags))
                    if conflicts < min_conflicts or (conflicts == min_conflicts and team["members"] < min_members):
                        best_team = team
                        min_conflicts = conflicts
                        min_members = team["members"]

            # 3. Если все свободные команды переполнены, ищем ЛЮБУЮ с минимальными конфликтами
            if not best_team:
                best_team = min(
                    [t for t in simulated_teams if self.color_limits[t["color"]] > 0],
                    key=lambda x: (
                        len(x["tags"].intersection(user_tags)),
                        x["members"]
                    ),
                    default=None
                )

            if not best_team:
                output.append(f"{user['user_id']} | {user.get('username', '')} | ❌ Нет доступных команд")
                continue

            # Проверка конфликтов
            status = []
            if best_team["members"] >= max_team_size:
                status.append("🟡 переполнение")
            if not best_team["tags"].isdisjoint(user_tags):
                status.append("⚠️ пересечение тегов команды")
            if not status:
                status.append("✅ OK")

            # Обновляем данные
            best_team["members"] += 1
            best_team["tags"].update(user_tags)

            output.append(
                f"{user['user_id']} | {user.get('username', '')} | {user['tags']} | "
                f"команда #{best_team['id']} ({best_team['color']}) {' + '.join(status)}"
            )

        return output

if __name__ == "__main__":
    with TestTeamDistributor() as distributor:
        # distributor.clear_all_teams()
        distributor.setup_colors({
            "Розовые": 1,
            "Жёлтые": 0,
            "Зелёные": 0,
            "Белые": 0,
        })
        result = distributor.simulate_distribution(max_team_size=2)
        for line in result:
            print(line)
