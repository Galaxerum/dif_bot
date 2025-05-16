import sqlite3
from collections import defaultdict
from typing import List, Dict, Any
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "main.db"


class TeamDistributor:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

    def setup_colors(self, colors: List[str]):
        """Инициализирует базовые цвета команд"""
        with self.conn:
            self.conn.execute("DELETE FROM teams")
            for color in colors:
                self.conn.execute(
                    "INSERT INTO teams (colors) VALUES (?)",
                    (color,)
                )

    def get_users_to_distribute(self) -> List[Dict]:
        """Возвращает пользователей для распределения"""
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
                "tags": row["tags"].split(",") if row["tags"] else []
            }
            for row in cur.fetchall()
        ]

    def get_team_stats(self) -> list[dict[str, Any]]:
        """Возвращает статистику по командам"""
        cur = self.conn.cursor()

        # Получаем количество участников в каждой команде
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

    def distribute_users(self, max_team_size: int = 10):
        """Распределяет пользователей по командам"""
        users = self.get_users_to_distribute()

        for user in users:
            try:
                # Получаем текущее распределение
                teams = self.get_team_stats()

                if not teams:
                    raise ValueError("Нет доступных команд. Сначала вызовите setup_colors()")

                # Находим команду с минимальным количеством участников
                best_team = min(teams, key=lambda x: x["members"])

                if best_team["members"] >= max_team_size:
                    # Если все команды заполнены, создаем новую с тем же цветом
                    color = best_team["color"]
                    self.conn.execute(
                        "INSERT INTO teams (colors) VALUES (?)",
                        (color,)
                    )
                    best_team_id = self.conn.lastrowid
                else:
                    best_team_id = best_team["id"]

                # Назначаем пользователя в команду
                with self.conn:
                    self.conn.execute(
                        "UPDATE users SET team_id = ? WHERE user_id = ?",
                        (best_team_id, user["user_id"])
                    )

                print(f"User {user['user_id']} assigned to team {best_team_id} (color: {best_team['color']})")
            except Exception as e:
                print(f"Failed to distribute user {user['user_id']}: {e}")


if __name__ == "__main__":
    # Пример использования
    with TeamDistributor() as distributor:
        # 1. Инициализация цветов команд
        distributor.setup_colors(["red", "blue", "green"])

        # 2. Распределение пользователей
        distributor.distribute_users(max_team_size=10)