/*
 * Vencord, a Discord client mod
 * Copyright (c) 2026 Vendicated and contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

import * as DataStore from "@api/DataStore";
import { Logger } from "@utils/Logger";

const STORE_KEY = "VoiceStreaks_data";
export const MAX_MONTHLY_RECOVERIES = 3;
export const FIRST_STREAK_DAY_SECONDS = 15 * 60;
export const CONTINUATION_DAY_SECONDS = 60;
const DAILY_HISTORY_DAYS = 15;

const logger = new Logger("VoiceStreaks");

export interface FriendStreak {
    pinned: boolean;
    streak: number;
    bestStreak: number;
    lastSharedDate: string;
    streakStartDate?: string;
    recoverableStreak: number;
    recoveryMonth: string;
    recoveriesUsed: number;
    totalVoiceSeconds: number;
    dailyVoiceSeconds: Record<string, number>;
}

export interface WeeklyFriendRecap {
    userId: string;
    seconds: number;
    activeDays: number;
}

export interface WeeklyRecap {
    weekStart: string;
    weekEnd: string;
    totalVoiceSeconds: number;
    activeDays: number;
    friends: WeeklyFriendRecap[];
}

export interface Achievement {
    minimum: number;
    title: string;
    description: string;
}

export type StreakStore = Record<string, FriendStreak>;

const ACHIEVEMENTS: Achievement[] = [
    { minimum: 1, title: "First spark", description: "Start a shared voice streak" },
    { minimum: 7, title: "Week together", description: "Keep a streak for seven days" },
    { minimum: 30, title: "Monthly regulars", description: "Keep a streak for thirty days" },
    { minimum: 100, title: "Violet flame", description: "Reach the 100-day violet tier" },
    { minimum: 365, title: "Year in voice", description: "Reach a full year together" },
    { minimum: 1000, title: "Legendary link", description: "Reach a 1,000-day streak" }
];

let streakCache: StreakStore = {};
let saveTimeout: ReturnType<typeof setTimeout> | null = null;
let saveQueue = Promise.resolve();
const listeners = new Set<() => void>();

export function subscribe(listener: () => void): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
}

export function refreshStreakViews(): void {
    listeners.forEach(listener => listener());
}

export function getUTCDateString(date: Date = new Date()): string {
    return date.toISOString().slice(0, 10);
}

export function getUTCMonthString(date: Date = new Date()): string {
    return date.toISOString().slice(0, 7);
}

function getUTCDateOffset(dateString: string, offsetDays: number): string {
    const date = new Date(`${dateString}T00:00:00.000Z`);
    date.setUTCDate(date.getUTCDate() + offsetDays);
    return getUTCDateString(date);
}

function getUTCYesterdayString(date: Date = new Date()): string {
    return getUTCDateOffset(getUTCDateString(date), -1);
}

function isDateString(value: unknown): value is string {
    return typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return value != null && typeof value === "object" && !Array.isArray(value);
}

function trimDailyHistory(dailyVoiceSeconds: Record<string, number>, today = getUTCDateString()): Record<string, number> {
    const oldestKeptDate = getUTCDateOffset(today, -(DAILY_HISTORY_DAYS - 1));
    return Object.fromEntries(
        Object.entries(dailyVoiceSeconds)
            .filter(([date, seconds]) => isDateString(date) && date >= oldestKeptDate && Number(seconds) > 0)
            .map(([date, seconds]) => [date, Math.max(0, Number(seconds) || 0)])
    );
}

function normalizeEntry(entry: Partial<FriendStreak> | undefined): FriendStreak {
    const rawEntry = (isRecord(entry) ? entry : {}) as Partial<FriendStreak> & {
        manuallyEdited?: unknown;
        historicalSeedDate?: unknown;
    };
    // Versions before this one allowed a manually edited number. Do not preserve a fake streak.
    if (rawEntry.manuallyEdited === true) {
        return {
            pinned: false,
            streak: 0,
            bestStreak: 0,
            lastSharedDate: "",
            recoverableStreak: 0,
            recoveryMonth: getUTCMonthString(),
            recoveriesUsed: 0,
            totalVoiceSeconds: Math.max(0, Number(rawEntry.totalVoiceSeconds) || 0),
            dailyVoiceSeconds: {}
        };
    }

    // Historical seed values were used by an older private build. They were
    // not earned from tracked voice time, so discard them during migration.
    const wasHistoricalSeed = isDateString(rawEntry.historicalSeedDate);
    const streak = wasHistoricalSeed ? 0 : Math.max(0, Number(rawEntry.streak) || 0);
    const lastSharedDate = wasHistoricalSeed ? "" : (isDateString(rawEntry.lastSharedDate) ? rawEntry.lastSharedDate : "");
    const streakStartDate = isDateString(rawEntry.streakStartDate) ? rawEntry.streakStartDate : undefined;

    return {
        pinned: rawEntry.pinned === true,
        streak,
        bestStreak: wasHistoricalSeed ? 0 : Math.max(streak, Number(rawEntry.bestStreak) || 0),
        lastSharedDate,
        ...(streakStartDate && !wasHistoricalSeed ? { streakStartDate } : {}),
        recoverableStreak: wasHistoricalSeed ? 0 : Math.max(0, Number(rawEntry.recoverableStreak) || 0),
        recoveryMonth: typeof rawEntry.recoveryMonth === "string" ? rawEntry.recoveryMonth : getUTCMonthString(),
        recoveriesUsed: Math.max(0, Number(rawEntry.recoveriesUsed) || 0),
        totalVoiceSeconds: Math.max(0, Number(rawEntry.totalVoiceSeconds) || 0),
        dailyVoiceSeconds: trimDailyHistory(isRecord(rawEntry.dailyVoiceSeconds) ? rawEntry.dailyVoiceSeconds as Record<string, number> : {})
    };
}

export async function loadStreaks(): Promise<void> {
    let migrated = false;

    try {
        const stored = await DataStore.get<StreakStore>(STORE_KEY);
        streakCache = Object.fromEntries(
            Object.entries(stored ?? {}).map(([userId, entry]) => {
                const rawEntry: Record<string, unknown> = isRecord(entry) ? entry : {};
                const normalized = normalizeEntry(rawEntry as Partial<FriendStreak>);
                migrated ||= rawEntry.manuallyEdited === true
                    || !Object.hasOwn(rawEntry, "dailyVoiceSeconds")
                    || !Object.hasOwn(rawEntry, "bestStreak")
                    || isDateString(rawEntry.historicalSeedDate);
                return [userId, normalized];
            })
        );
    } catch (error) {
        streakCache = {};
        logger.error("Failed to load saved streaks", error);
    }

    if (migrated) scheduleSave();
    refreshStreakViews();
}

function getSnapshot(): StreakStore {
    return Object.fromEntries(
        Object.entries(streakCache).map(([userId, entry]) => [userId, {
            ...entry,
            dailyVoiceSeconds: { ...entry.dailyVoiceSeconds }
        }])
    );
}

function persistStreaks(): Promise<void> {
    const snapshot = getSnapshot();
    saveQueue = saveQueue
        .then(() => DataStore.set(STORE_KEY, snapshot))
        .catch(error => logger.error("Failed to save streaks", error));
    return saveQueue;
}

function scheduleSave(): void {
    if (saveTimeout) clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => {
        saveTimeout = null;
        void persistStreaks();
    }, 2000);
}

function getOrCreate(userId: string): FriendStreak {
    return streakCache[userId] ?? (streakCache[userId] = normalizeEntry(undefined));
}

function resetRecoveryMonth(entry: FriendStreak): void {
    const month = getUTCMonthString();
    if (entry.recoveryMonth !== month) {
        entry.recoveryMonth = month;
        entry.recoveriesUsed = 0;
    }
}

function hasActiveStreak(entry: FriendStreak, date = new Date()): boolean {
    const today = getUTCDateString(date);
    return entry.lastSharedDate === today || entry.lastSharedDate === getUTCYesterdayString(date);
}

function getRecoverableStreak(entry: FriendStreak): number {
    return hasActiveStreak(entry) ? entry.recoverableStreak : Math.max(entry.recoverableStreak, entry.streak);
}

function qualifyDate(entry: FriendStreak, date: string): boolean {
    if (entry.lastSharedDate === date) return false;

    const isContinuation = entry.streak > 0 && entry.lastSharedDate === getUTCDateOffset(date, -1);
    const requiredSeconds = isContinuation ? CONTINUATION_DAY_SECONDS : FIRST_STREAK_DAY_SECONDS;
    if ((entry.dailyVoiceSeconds[date] ?? 0) < requiredSeconds) return false;

    if (isContinuation) {
        entry.streak += 1;
    } else {
        entry.recoverableStreak = Math.max(entry.recoverableStreak, entry.streak);
        entry.streak = 1;
        entry.streakStartDate = date;
    }

    entry.lastSharedDate = date;
    entry.bestStreak = Math.max(entry.bestStreak, entry.streak);
    return true;
}

function getNextUtcBoundary(time: number): number {
    const date = new Date(time);
    return Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate() + 1);
}

export function recordSharedVoiceInterval(userId: string, startedAt: number, endedAt: number): void {
    if (!Number.isFinite(startedAt) || !Number.isFinite(endedAt) || endedAt <= startedAt) return;

    const entry = getOrCreate(userId);
    resetRecoveryMonth(entry);
    let cursor = startedAt;
    let changed = false;

    while (cursor < endedAt) {
        const date = getUTCDateString(new Date(cursor));
        const segmentEnd = Math.min(endedAt, getNextUtcBoundary(cursor));
        const seconds = (segmentEnd - cursor) / 1000;

        entry.totalVoiceSeconds += seconds;
        entry.dailyVoiceSeconds[date] = (entry.dailyVoiceSeconds[date] ?? 0) + seconds;
        if (qualifyDate(entry, date)) changed = true;
        cursor = segmentEnd;
    }

    entry.dailyVoiceSeconds = trimDailyHistory(entry.dailyVoiceSeconds);
    scheduleSave();
    if (changed || endedAt > startedAt) refreshStreakViews();
}

export function getRawStreak(userId: string): FriendStreak | undefined {
    return streakCache[userId];
}

export function getActiveStreakCount(userId: string): number {
    const entry = streakCache[userId];
    return entry && hasActiveStreak(entry) ? entry.streak : 0;
}

export function getMonthlyRecoveryState(userId: string): { used: number; remaining: number; recoverable: number; } {
    const entry = streakCache[userId];
    if (!entry) return { used: 0, remaining: MAX_MONTHLY_RECOVERIES, recoverable: 0 };

    const used = entry.recoveryMonth === getUTCMonthString() ? entry.recoveriesUsed : 0;
    return {
        used,
        remaining: Math.max(0, MAX_MONTHLY_RECOVERIES - used),
        recoverable: getRecoverableStreak(entry)
    };
}

export function restoreStreak(userId: string): boolean {
    const entry = streakCache[userId];
    if (!entry) return false;

    resetRecoveryMonth(entry);
    const recoverableStreak = getRecoverableStreak(entry);
    if (hasActiveStreak(entry) || recoverableStreak <= 0 || entry.recoveriesUsed >= MAX_MONTHLY_RECOVERIES) {
        return false;
    }

    entry.streak = recoverableStreak;
    entry.bestStreak = Math.max(entry.bestStreak, entry.streak);
    entry.lastSharedDate = getUTCYesterdayString();
    entry.recoveriesUsed += 1;
    entry.streakStartDate ??= getUTCDateOffset(entry.lastSharedDate, -(Math.max(0, entry.streak - 1)));
    scheduleSave();
    refreshStreakViews();
    return true;
}

export function togglePinnedFriend(userId: string): boolean {
    const entry = getOrCreate(userId);
    entry.pinned = !entry.pinned;
    scheduleSave();
    refreshStreakViews();
    return entry.pinned;
}

function getPreviousWeekRange(now = new Date()): { weekStart: string; weekEnd: string; } {
    const today = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
    const daysSinceMonday = (today.getUTCDay() + 6) % 7;
    today.setUTCDate(today.getUTCDate() - daysSinceMonday - 7);
    const weekStart = getUTCDateString(today);
    const weekEnd = getUTCDateOffset(weekStart, 6);
    return { weekStart, weekEnd };
}

export function getWeeklyRecap(now = new Date()): WeeklyRecap {
    const { weekStart, weekEnd } = getPreviousWeekRange(now);
    const friends = Object.entries(streakCache)
        .map(([userId, entry]) => {
            let seconds = 0;
            let activeDays = 0;
            for (let date = weekStart; date <= weekEnd; date = getUTCDateOffset(date, 1)) {
                const daySeconds = entry.dailyVoiceSeconds[date] ?? 0;
                seconds += daySeconds;
                if (daySeconds > 0) activeDays++;
            }
            return { userId, seconds, activeDays };
        })
        .filter(friend => friend.seconds > 0)
        .toSorted((a, b) => b.seconds - a.seconds);

    return {
        weekStart,
        weekEnd,
        totalVoiceSeconds: friends.reduce((total, friend) => total + friend.seconds, 0),
        activeDays: new Set(
            Object.values(streakCache).flatMap(entry => Object.keys(entry.dailyVoiceSeconds)
                .filter(date => date >= weekStart && date <= weekEnd && entry.dailyVoiceSeconds[date] > 0))
        ).size,
        friends
    };
}

export function getAchievements(userId: string): Achievement[] {
    const bestStreak = streakCache[userId]?.bestStreak ?? 0;
    return ACHIEVEMENTS.filter(achievement => bestStreak >= achievement.minimum);
}

export function getStreakSummary(userId: string) {
    const entry = getRawStreak(userId);
    return {
        pinned: entry?.pinned ?? false,
        streak: getActiveStreakCount(userId),
        bestStreak: entry?.bestStreak ?? 0,
        streakStartDate: entry?.streakStartDate,
        totalVoiceSeconds: entry?.totalVoiceSeconds ?? 0,
        recovery: getMonthlyRecoveryState(userId)
    };
}

export async function flushAndCleanup(): Promise<void> {
    if (saveTimeout) {
        clearTimeout(saveTimeout);
        saveTimeout = null;
    }
    await persistStreaks();
}
