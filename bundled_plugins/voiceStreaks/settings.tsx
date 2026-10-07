/*
 * Vencord, a Discord client mod
 * Copyright (c) 2026 Vendicated and contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

import { definePluginSettings } from "@api/Settings";
import { Button } from "@components/Button";
import { copyWithToast } from "@utils/discord";
import { OptionType } from "@utils/types";
import { Forms, LocaleStore, React, RelationshipStore, TabBar, UserStore } from "@webpack/common";

import { FriendRecoveryButton, getStreakTier, useStreakUpdates } from "./components";
import {
    getAchievements,
    getStreakSummary,
    getWeeklyRecap,
    MAX_MONTHLY_RECOVERIES,
    togglePinnedFriend
} from "./streakManager";

const enum SettingsTab {
    Friends = "friends",
    Leaders = "leaders",
    Weekly = "weekly",
    Achievements = "achievements"
}

const gridStyle = {
    display: "grid",
    gridTemplateColumns: "minmax(140px, 1.4fr) 72px 72px 92px 88px 112px",
    gap: 8,
    alignItems: "center",
    padding: "8px 0",
    borderBottom: "1px solid var(--background-modifier-accent)"
} as const;

const leaderGridStyle = {
    ...gridStyle,
    gridTemplateColumns: "36px minmax(140px, 1fr) 110px 72px"
} as const;

const ru = {
    friends: "Друзья",
    leaders: "Лидеры",
    weekly: "Неделя",
    achievements: "Достижения",
    noFriends: "Нет друзей Discord.",
    handle: "Тег",
    current: "Сейчас",
    best: "Рекорд",
    since: "С",
    voice: "В войсе",
    recovery: "Возврат",
    pin: "Закрепить",
    unpin: "Открепить",
    copySummary: "Скопировать сводку",
    copied: "Сводка скопирована",
    weeklyRange: "UTC",
    together: "вместе",
    activeDays: "активных дней",
    noWeek: "За эту неделю общего войса не было.",
    rank: "Место",
    flame: "Огонёк",
    noAchievements: "Пока нет достижений.",
    rules: "Первый день — 15 мин.; продолжение — 1 мин.; UTC.",
    summaryTitle: "VoiceStreaks — моя статистика",
    summaryTotal: "Всего в войсе вместе",
    summaryBest: "Лучший огонёк",
    summaryTop: "Топ друзей по времени",
    summaryNone: "пока нет данных",
    daysShort: "дн."
};

type Copy = Record<keyof typeof ru, string>;

const en: Copy = {
    friends: "Friends",
    leaders: "Leaders",
    weekly: "Weekly recap",
    achievements: "Achievements",
    noFriends: "No Discord friends found.",
    handle: "Discord handle",
    current: "Current",
    best: "Best",
    since: "Since",
    voice: "Voice time",
    recovery: "Recovery",
    pin: "Pin",
    unpin: "Unpin",
    copySummary: "Copy summary",
    copied: "Summary copied",
    weeklyRange: "UTC",
    together: "together",
    activeDays: "active days",
    noWeek: "No shared voice time this week.",
    rank: "Rank",
    flame: "Streak",
    noAchievements: "No achievements yet.",
    rules: "First day: 15 min; continuation: 1 min; UTC.",
    summaryTitle: "VoiceStreaks — my stats",
    summaryTotal: "Total voice time together",
    summaryBest: "Best streak",
    summaryTop: "Top friends by voice time",
    summaryNone: "no data yet",
    daysShort: "d"
};

function isRussian(): boolean {
    return LocaleStore.locale.toLowerCase().startsWith("ru");
}

function getCopy(): Copy {
    return isRussian() ? ru : en;
}

function formatHours(seconds: number, russian = isRussian()): string {
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    return russian ? `${hours} ч ${minutes % 60} мин` : `${hours}h ${minutes % 60}m`;
}

function formatDays(days: number, copy: Copy): string {
    return `${days} ${copy.daysShort}`;
}

function getAchievementTitle(minimum: number, russian = isRussian()): string {
    const titles: Record<number, [string, string]> = {
        1: ["Первая искра", "First spark"],
        7: ["Неделя вместе", "Week together"],
        30: ["Постоянные игроки", "Monthly regulars"],
        100: ["Фиолетовый огонь", "Violet flame"],
        365: ["Год в войсе", "Year in voice"],
        1000: ["Легендарная связь", "Legendary link"]
    };
    return titles[minimum]?.[russian ? 0 : 1] ?? String(minimum);
}

function FriendHandle({ userId }: { userId: string; }) {
    const user = UserStore.getUser(userId);
    return <span>{user?.username ?? "Unknown user"}</span>;
}

function getSortedFriendIds(friendIds: string[]): string[] {
    return [...friendIds].toSorted((leftId, rightId) => {
        const left = getStreakSummary(leftId);
        const right = getStreakSummary(rightId);
        if (left.pinned !== right.pinned) return Number(right.pinned) - Number(left.pinned);
        if (left.totalVoiceSeconds !== right.totalVoiceSeconds) return right.totalVoiceSeconds - left.totalVoiceSeconds;
        return (UserStore.getUser(leftId)?.username ?? leftId).localeCompare(UserStore.getUser(rightId)?.username ?? rightId);
    });
}

function PinButton({ userId, pinned, copy }: { userId: string; pinned: boolean; copy: Copy; }) {
    return (
        <Button size="small" onClick={() => togglePinnedFriend(userId)}>
            {pinned ? copy.unpin : copy.pin}
        </Button>
    );
}

function FriendsTab({ copy }: { copy: Copy; }) {
    const friendIds = getSortedFriendIds(RelationshipStore.getFriendIDs());
    if (friendIds.length === 0) return <Forms.FormText>{copy.noFriends}</Forms.FormText>;

    return (
        <div>
            <div style={{ ...gridStyle, color: "var(--text-muted)", fontSize: 12 }}>
                <span>{copy.handle}</span>
                <span>{copy.current}</span>
                <span>{copy.best}</span>
                <span>{copy.since}</span>
                <span>{copy.voice}</span>
                <span>{copy.recovery}</span>
            </div>
            {friendIds.map(userId => {
                const { pinned, streak, bestStreak, streakStartDate, totalVoiceSeconds, recovery } = getStreakSummary(userId);
                const tier = streak > 0 ? getStreakTier(streak) : null;
                return (
                    <div key={userId} style={gridStyle}>
                        <FriendHandle userId={userId} />
                        <span style={tier ? { color: tier.color, fontWeight: 700 } : undefined}>{streak > 0 ? formatDays(streak, copy) : "—"}</span>
                        <span>{bestStreak > 0 ? formatDays(bestStreak, copy) : "—"}</span>
                        <span>{streakStartDate ?? "—"}</span>
                        <span>{formatHours(totalVoiceSeconds)}</span>
                        <span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
                            <PinButton userId={userId} pinned={pinned} copy={copy} />
                            {recovery.used}/{MAX_MONTHLY_RECOVERIES}
                            <FriendRecoveryButton userId={userId} />
                        </span>
                    </div>
                );
            })}
        </div>
    );
}

function LeadersTab({ copy }: { copy: Copy; }) {
    const friendIds = getSortedFriendIds(RelationshipStore.getFriendIDs());
    if (friendIds.length === 0) return <Forms.FormText>{copy.noFriends}</Forms.FormText>;

    return (
        <div>
            <div style={{ ...leaderGridStyle, color: "var(--text-muted)", fontSize: 12 }}>
                <span>{copy.rank}</span>
                <span>{copy.handle}</span>
                <span>{copy.voice}</span>
                <span>{copy.flame}</span>
            </div>
            {friendIds.map((userId, index) => {
                const { streak, totalVoiceSeconds } = getStreakSummary(userId);
                const tier = streak > 0 ? getStreakTier(streak) : null;
                return (
                    <div key={userId} style={leaderGridStyle}>
                        <span>{index + 1}</span>
                        <FriendHandle userId={userId} />
                        <span>{formatHours(totalVoiceSeconds)}</span>
                        <span style={tier ? { color: tier.color, fontWeight: 700 } : undefined}>{streak > 0 ? formatDays(streak, copy) : "—"}</span>
                    </div>
                );
            })}
        </div>
    );
}

function WeeklyTab({ copy }: { copy: Copy; }) {
    const recap = getWeeklyRecap();
    return (
        <div>
            <Forms.FormText>{recap.weekStart} — {recap.weekEnd} {copy.weeklyRange}</Forms.FormText>
            <div style={{ display: "flex", gap: 24, margin: "12px 0" }}>
                <span><strong>{formatHours(recap.totalVoiceSeconds)}</strong> {copy.together}</span>
                <span><strong>{recap.activeDays}</strong> {copy.activeDays}</span>
            </div>
            {recap.friends.length === 0
                ? <Forms.FormText>{copy.noWeek}</Forms.FormText>
                : recap.friends.map(friend => (
                    <div key={friend.userId} style={{ ...gridStyle, gridTemplateColumns: "minmax(150px, 1fr) 100px 100px" }}>
                        <FriendHandle userId={friend.userId} />
                        <span>{formatHours(friend.seconds)}</span>
                        <span>{friend.activeDays} {copy.activeDays}</span>
                    </div>
                ))}
        </div>
    );
}

function AchievementsTab({ copy }: { copy: Copy; }) {
    const friendIds = getSortedFriendIds(RelationshipStore.getFriendIDs());
    const entries = friendIds.map(userId => ({ userId, achievements: getAchievements(userId) }))
        .filter(entry => entry.achievements.length > 0);

    if (entries.length === 0) return <Forms.FormText>{copy.noAchievements}</Forms.FormText>;

    return (
        <div>
            {entries.map(({ userId, achievements }) => (
                <div key={userId} style={{ padding: "12px 0", borderBottom: "1px solid var(--background-modifier-accent)" }}>
                    <strong><FriendHandle userId={userId} /></strong>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
                        {achievements.map(achievement => (
                            <span
                                key={achievement.minimum}
                                title={getAchievementTitle(achievement.minimum)}
                                style={{
                                    padding: "3px 7px",
                                    borderRadius: 8,
                                    background: "var(--background-modifier-accent)",
                                    color: "var(--text-normal)",
                                    fontSize: 12
                                }}
                            >
                                {getAchievementTitle(achievement.minimum)}
                            </span>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}

function makeExportSummary(friendIds: string[], copy: Copy): string {
    const ranked = getSortedFriendIds(friendIds).map(userId => ({
        userId,
        username: UserStore.getUser(userId)?.username ?? "Unknown user",
        ...getStreakSummary(userId)
    }));
    const totalVoiceSeconds = ranked.reduce((total, friend) => total + friend.totalVoiceSeconds, 0);
    const best = ranked.toSorted((left, right) => right.bestStreak - left.bestStreak)[0];
    const top = ranked.filter(friend => friend.totalVoiceSeconds > 0).slice(0, 3);
    const bestLine = best && best.bestStreak > 0
        ? `${formatDays(best.bestStreak, copy)} — ${best.username}`
        : copy.summaryNone;
    const topLines = top.length > 0
        ? top.map((friend, index) => `${index + 1}. ${friend.username} — ${formatHours(friend.totalVoiceSeconds)}`).join("\n")
        : copy.summaryNone;

    return [
        copy.summaryTitle,
        `${copy.summaryTotal}: ${formatHours(totalVoiceSeconds)}`,
        `${copy.summaryBest}: ${bestLine}`,
        `${copy.summaryTop}:`,
        topLines
    ].join("\n");
}

function VoiceStreaksSettings() {
    useStreakUpdates();
    const [currentTab, setCurrentTab] = React.useState(SettingsTab.Friends);
    const copy = getCopy();
    const friendIds = RelationshipStore.getFriendIDs();

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <Button size="small" onClick={() => void copyWithToast(makeExportSummary(friendIds, copy), copy.copied)}>
                    {copy.copySummary}
                </Button>
            </div>
            <TabBar type="top" look="brand" selectedItem={currentTab} onItemSelect={setCurrentTab}>
                <TabBar.Item id={SettingsTab.Friends}>{copy.friends}</TabBar.Item>
                <TabBar.Item id={SettingsTab.Leaders}>{copy.leaders}</TabBar.Item>
                <TabBar.Item id={SettingsTab.Weekly}>{copy.weekly}</TabBar.Item>
                <TabBar.Item id={SettingsTab.Achievements}>{copy.achievements}</TabBar.Item>
            </TabBar>
            {currentTab === SettingsTab.Friends && <FriendsTab copy={copy} />}
            {currentTab === SettingsTab.Leaders && <LeadersTab copy={copy} />}
            {currentTab === SettingsTab.Weekly && <WeeklyTab copy={copy} />}
            {currentTab === SettingsTab.Achievements && <AchievementsTab copy={copy} />}
            <Forms.FormText>{copy.rules}</Forms.FormText>
        </div>
    );
}

export const settings = definePluginSettings({
    dashboard: {
        type: OptionType.COMPONENT,
        component: VoiceStreaksSettings
    }
});
