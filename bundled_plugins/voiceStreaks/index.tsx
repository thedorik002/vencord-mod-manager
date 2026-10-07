/*
 * Vencord, a Discord client mod
 * Copyright (c) 2026 Vendicated and contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

import { Devs } from "@utils/constants";
import definePlugin from "@utils/types";
import { FluxDispatcher, RelationshipStore, UserStore, VoiceStateStore } from "@webpack/common";

import { StreakIndicator } from "./components";
import { settings } from "./settings";
import {
    flushAndCleanup,
    loadStreaks,
    recordSharedVoiceInterval,
    refreshStreakViews
} from "./streakManager";

const ACTIVE_RECONCILIATION_MS = 60_000;

const activeVoiceSince = new Map<string, number>();
let activeTimer: ReturnType<typeof setInterval> | null = null;
let utcRolloverTimer: ReturnType<typeof setTimeout> | null = null;

function isFriend(userId: string): boolean {
    return RelationshipStore.getFriendIDs().includes(userId);
}

function updateActiveTimer(): void {
    if (activeVoiceSince.size > 0 && !activeTimer) {
        activeTimer = setInterval(reconcileVoice, ACTIVE_RECONCILIATION_MS);
    } else if (activeVoiceSince.size === 0 && activeTimer) {
        clearInterval(activeTimer);
        activeTimer = null;
    }
}

function finishInterval(userId: string, startedAt: number, endedAt: number): void {
    recordSharedVoiceInterval(userId, startedAt, endedAt);
}

function reconcileVoice(): void {
    const me = UserStore.getCurrentUser();
    const myChannelId = VoiceStateStore.getVoiceStateForUser(me?.id)?.channelId;
    const now = Date.now();
    const friendIds = RelationshipStore.getFriendIDs();
    const friendIdSet = new Set(friendIds);

    for (const userId of friendIds) {
        const friendChannelId = VoiceStateStore.getVoiceStateForUser(userId)?.channelId;
        const sharingVoice = myChannelId != null && myChannelId === friendChannelId;
        const startedAt = activeVoiceSince.get(userId);

        if (sharingVoice) {
            if (startedAt == null) {
                activeVoiceSince.set(userId, now);
            } else {
                finishInterval(userId, startedAt, now);
                activeVoiceSince.set(userId, now);
            }
        } else if (startedAt != null) {
            finishInterval(userId, startedAt, now);
            activeVoiceSince.delete(userId);
        }
    }

    for (const [userId, startedAt] of activeVoiceSince) {
        if (!friendIdSet.has(userId)) {
            finishInterval(userId, startedAt, now);
            activeVoiceSince.delete(userId);
        }
    }

    updateActiveTimer();
    refreshStreakViews();
}

function scheduleUtcRollover(): void {
    if (utcRolloverTimer) clearTimeout(utcRolloverTimer);

    const now = new Date();
    const nextMidnight = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1, 0, 0, 1);
    utcRolloverTimer = setTimeout(() => {
        utcRolloverTimer = null;
        reconcileVoice();
        refreshStreakViews();
        scheduleUtcRollover();
    }, nextMidnight - Date.now());
}

export default definePlugin({
    name: "VoiceStreaks",
    description: "Tracks consecutive UTC voice days and local milestones with Discord friends",
    tags: ["Voice", "Friends", "Appearance"],
    authors: [Devs.Ven],
    settings,

    patches: [
        {
            find: "#{intl::USER_PROFILE_PRONOUNS}",
            replacement: {
                match: /(user:(\i).{0,100}onClickDisplayName:\i,trailing:)(\i)/,
                replace: "$1[$self.renderProfileStreak({userId:$2.id,isProfile:true}),$3]"
            }
        },
        {
            // Stable i18n anchor used by Vencord's voice-name color integration.
            // If Discord changes this row, the patch can fail without affecting tracking.
            find: "#{intl::GUEST_NAME_SUFFIX})]",
            replacement: {
                match: /(#{intl::GUEST_NAME_SUFFIX}.{0,50}?""(?=\])(?<=guildId:(\i),.+?user:(\i).+?))/,
                replace: "$1,$self.renderVoiceStreak({userId:$3.id,isVoice:true})"
            }
        }
    ],

    renderProfileStreak: StreakIndicator,
    renderVoiceStreak: StreakIndicator,

    start: async () => {
        await loadStreaks();
        reconcileVoice();
        scheduleUtcRollover();
        FluxDispatcher.subscribe("VOICE_STATE_UPDATES", reconcileVoice);
        FluxDispatcher.subscribe("RELATIONSHIP_ADD", reconcileVoice);
        FluxDispatcher.subscribe("RELATIONSHIP_REMOVE", reconcileVoice);
    },

    stop: async () => {
        const now = Date.now();
        for (const [userId, startedAt] of activeVoiceSince) {
            finishInterval(userId, startedAt, now);
        }
        activeVoiceSince.clear();

        if (activeTimer) clearInterval(activeTimer);
        activeTimer = null;
        if (utcRolloverTimer) clearTimeout(utcRolloverTimer);
        utcRolloverTimer = null;

        FluxDispatcher.unsubscribe("VOICE_STATE_UPDATES", reconcileVoice);
        FluxDispatcher.unsubscribe("RELATIONSHIP_ADD", reconcileVoice);
        FluxDispatcher.unsubscribe("RELATIONSHIP_REMOVE", reconcileVoice);
        await flushAndCleanup();
    }
});
