/*
 * Vencord, a Discord client mod
 * Copyright (c) 2026 Vendicated and contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

import { Button } from "@components/Button";
import ErrorBoundary from "@components/ErrorBoundary";
import { LocaleStore, React, RelationshipStore, Tooltip } from "@webpack/common";

import { getActiveStreakCount, getMonthlyRecoveryState, restoreStreak, subscribe } from "./streakManager";

export interface StreakTier {
    label: string;
    color: string;
}

const STREAK_TIERS: Array<StreakTier & { minimum: number; }> = [
    { minimum: 1000, label: "Golden", color: "#f4c84a" },
    { minimum: 365, label: "Blue", color: "#4dcfff" },
    { minimum: 100, label: "Violet", color: "#b18cff" },
    { minimum: 30, label: "Red", color: "#ff6b6b" },
    { minimum: 2, label: "Orange", color: "#ff8a00" },
    { minimum: 1, label: "Gray", color: "var(--text-muted)" }
];

function Fire({ size, color }: { size: number; color: string; }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
                d="M12 2C10.97 6.81 6 8.44 6 13.5C6 16.54 8.46 19 11.5 19H12.5C15.54 19 18 16.54 18 13.5C18 8.44 13.03 6.81 12 2ZM12 17C10.34 17 9 15.66 9 14C9 12.07 10.53 10.64 12 9.34C13.47 10.64 15 12.07 15 14C15 15.66 13.66 17 12 17Z"
                fill={color}
            />
        </svg>
    );
}

export function useStreakUpdates(): void {
    const [, forceUpdate] = React.useReducer(count => count + 1, 0);
    React.useEffect(() => subscribe(forceUpdate), []);
}

export function getStreakTier(streak: number): StreakTier {
    return STREAK_TIERS.find(tier => streak >= tier.minimum) ?? STREAK_TIERS.at(-1)!;
}

function isRussian(): boolean {
    return LocaleStore.locale.toLowerCase().startsWith("ru");
}

function getTierLabel(tier: StreakTier, russian: boolean): string {
    if (!russian) return tier.label;

    return ({
        Golden: "Золотой",
        Blue: "Синий",
        Violet: "Фиолетовый",
        Red: "Красный",
        Orange: "Оранжевый",
        Gray: "Серый"
    } as const)[tier.label] ?? tier.label;
}

function isFriend(userId: string): boolean {
    return RelationshipStore.getFriendIDs().includes(userId);
}

export interface StreakIndicatorProps {
    userId: string;
    isProfile?: boolean;
    isVoice?: boolean;
}

export const StreakIndicator = ErrorBoundary.wrap(({ userId, isProfile, isVoice }: StreakIndicatorProps) => {
    useStreakUpdates();

    if (!isFriend(userId)) return null;

    const streak = getActiveStreakCount(userId);
    if (streak <= 0) return null;

    const tier = getStreakTier(streak);
    const russian = isRussian();
    const fireSize = isVoice ? 11 : 16;
    const label = russian
        ? `Голосовой огонёк: ${streak} ${streak === 1 ? "день" : "дней"} подряд. ${getTierLabel(tier, true)} уровень.`
        : `Voice streak: ${streak} day${streak === 1 ? "" : "s"} in a row. ${tier.label} tier.`;
    const content = (
        <span
            aria-label={label}
            style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 2,
                marginLeft: 4,
                lineHeight: 1,
                whiteSpace: "nowrap"
            }}
        >
            <Fire size={fireSize} color={tier.color} />
            <span style={{ color: tier.color, fontWeight: 700, fontSize: isVoice ? 9 : 13 }}>{streak}</span>
        </span>
    );

    return (
        <Tooltip text={label}>
            {props => <span {...props}>{content}</span>}
        </Tooltip>
    );
}, { noop: true });

export function FriendRecoveryButton({ userId }: { userId: string; }) {
    useStreakUpdates();
    const state = getMonthlyRecoveryState(userId);
    if (state.recoverable <= 0 || state.remaining <= 0 || getActiveStreakCount(userId) > 0) return null;
    return (
        <Button size="small" onClick={() => restoreStreak(userId)}>
            {isRussian() ? `Восстановить (${state.remaining})` : `Restore (${state.remaining})`}
        </Button>
    );
}
