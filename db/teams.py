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
            for color in color_limits:
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
        users = self.get_users_to_distribute()
        teams = self.get_team_stats()
        if not teams:
            raise ValueError("Нет доступных команд. Сначала вызовите setup_colors()")

        for user in users:
            user_tags = set(user["tags"])
            teams = self.get_team_stats()  # обновляем актуальные данные по командам

            # Ищем команду с местом и без пересечения тегов
            suitable_team = None
            for team in teams:
                if team["members"] >= max_team_size:
                    continue
                team_tags = self.get_team_tags(team["id"])
                if team_tags.isdisjoint(user_tags):
                    suitable_team = team
                    break

            if suitable_team is None:
                # Нет команды без пересечений — ищем команду с минимальным участием
                suitable_team = min(teams, key=lambda x: x["members"])

                # Если команда переполнена, пытаемся создать новую того же цвета
                if suitable_team["members"] >= max_team_size:
                    color = suitable_team["color"]
                    current_count = self.get_color_team_count(color)
                    limit = self.color_limits.get(color, 0)
                    if current_count < limit:
                        with self.conn:
                            self.conn.execute("INSERT INTO teams (colors) VALUES (?)", (color,))
                            new_team_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                        suitable_team = {
                            "id": new_team_id,
                            "color": color,
                            "members": 0
                        }
                    else:
                        # Если лимит достигнут, оставляем пользователя в самой маленькой команде
                        pass

            with self.conn:
                self.conn.execute(
                    "UPDATE users SET team_id = ? WHERE user_id = ?",
                    (suitable_team["id"], user["user_id"])
                )
            print(f"User {user['user_id']} assigned to team {suitable_team['id']} (color: {suitable_team['color']})")

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

        if not teams:
            teams = []
            team_id = 1
            for color, limit in self.color_limits.items():
                for _ in range(limit):
                    teams.append({"id": team_id, "color": color, "members": 0, "tags": set()})
                    team_id += 1

        simulated_teams = [team.copy() for team in teams]
        for team in simulated_teams:
            team["tags"] = set()

        output = []

        for user in users:
            user_tags = set(user["tags"])

            # Ищем первую команду с местом и без пересечений
            found_team = None
            for team in simulated_teams:
                if team["members"] < max_team_size and team["tags"].isdisjoint(user_tags):
                    found_team = team
                    break

            if not found_team:
                # Если не нашли подходящую, берем команду с минимальным количеством участников
                found_team = min(simulated_teams, key=lambda x: x["members"])
                # Можно добавить предупреждение, что пересечения есть
                output.append(
                    f"{user['user_id']} | {user['username']} | {user['tags']} | ⚠️ добавлен в команду с пересечениями #{found_team['id']} ({found_team['color']})")
            else:
                output.append(
                    f"{user['user_id']} | {user['username']} {user['tags']} | команда #{found_team['id']} ({found_team['color']})")

            # Добавляем пользователя в команду
            found_team["members"] += 1
            found_team["tags"].update(user_tags)

        return output


if __name__ == "__main__":
    with TestTeamDistributor() as distributor:
        # distributor.clear_all_teams()
        distributor.setup_colors({
            "red": 0,
            "blue": 1,
            "green": 1
        })

        result = distributor.simulate_distribution(max_team_size=2)
        for line in result:
            print(line)
