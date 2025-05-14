from db.users import get_all_users_without_team
from db.tags import get_user_tags, get_all_tags, save_new_tags
from db.teams import create_team, add_user_to_team, get_incomplete_teams, is_team_full
from collections import defaultdict


async def get_stable_tags(limit: int = 10) -> set:
    """
    Получает устойчивый набор тегов на основе первых N пользователей.
    """
    all_users = await get_all_users_without_team()
    tag_counter = defaultdict(int)
    for user in all_users[:limit]:
        tags = await get_user_tags(user.id)
        for tag in tags:
            tag_counter[tag] += 1

    stable_tags = {tag for tag, count in tag_counter.items() if count > 1}
    return stable_tags


async def filter_new_tags(user_id: int, stable_tags: set) -> list:
    """
    Возвращает отфильтрованные уникальные теги пользователя.
    """
    user_tags = await get_user_tags(user_id)
    new_tags = [tag for tag in user_tags if tag not in stable_tags]
    await save_new_tags(user_id, new_tags)
    return new_tags


async def form_teams():
    """
    Формирует команды по 10 человек с разнообразием тегов.
    """
    users = await get_all_users_without_team()
    tag_to_users = defaultdict(list)

    # Сгруппировать пользователей по тегам
    for user in users:
        tags = await get_user_tags(user.id)
        for tag in tags:
            tag_to_users[tag].append(user)

    used_users = set()
    teams = []

    while len(used_users) + 10 <= len(users):
        team = []
        covered_tags = set()

        for tag, tagged_users in tag_to_users.items():
            for user in tagged_users:
                if user.id not in used_users and len(team) < 10 and tag not in covered_tags:
                    team.append(user)
                    covered_tags.update(await get_user_tags(user.id))
                    used_users.add(user.id)
                    break

        if len(team) == 10:
            team_id = await create_team()
            for member in team:
                await add_user_to_team(member.id, team_id)
            teams.append(team_id)

    return teams


async def try_add_to_existing_team(user_id: int) -> bool:
    """
    Добавляет пользователя в существующую неполную команду.
    Возвращает True, если удалось добавить.
    """
    incomplete = await get_incomplete_teams()
    user_tags = await get_user_tags(user_id)

    for team in incomplete:
        team_members = team.members
        team_tags = set()
        for member in team_members:
            team_tags.update(await get_user_tags(member.id))

        # Проверяем, добавит ли пользователь новые теги
        if not set(user_tags).issubset(team_tags):
            await add_user_to_team(user_id, team.id)
            return True

    return False
