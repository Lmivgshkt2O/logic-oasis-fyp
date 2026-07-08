import 'package:flutter/material.dart';
import 'package:logic_oasis/app/logic_oasis_design.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/recommended_mission.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/widgets/logic_oasis_figma_components.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key, required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    return LogicOasisScaffold(
      children: [
        Row(
          children: [
            const SproutAvatar(size: 60),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Good morning,',
                    style: TextStyle(
                      color: LogicOasisDesign.body,
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${state.studentName} *',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: LogicOasisDesign.ink,
                      fontSize: 24,
                      fontWeight: FontWeight.w900,
                      height: 1.05,
                    ),
                  ),
                ],
              ),
            ),
            SoftIconButton(
              icon: state.missionReminders
                  ? Icons.notifications_active_rounded
                  : Icons.notifications_off_rounded,
              onTap: () => _toggleMissionReminders(context),
            ),
            const SizedBox(width: 10),
            SoftIconButton(
              icon: Icons.settings_rounded,
              onTap: () => state.changeTab(2),
            ),
          ],
        ),
        const SizedBox(height: 14),
        Row(
          children: [
            Expanded(
              child: StatCard(
                compact: true,
                icon: Icons.diamond_rounded,
                iconColor: const Color(0xFF36BFE2),
                value: '${state.crystals}',
                label: 'Crystals',
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: StatCard(
                compact: true,
                icon: Icons.bolt_rounded,
                iconColor: const Color(0xFFFFB92E),
                value: '${state.mutualAidEnergy}',
                label: 'Energy',
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: StatCard(
                compact: true,
                icon: Icons.local_fire_department_rounded,
                iconColor: const Color(0xFFFF6B4A),
                value: '${state.currentYearAttempts.length}',
                label: 'Day Streak',
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        OasisHeroCard(
          progress: state.restorationProgress,
          areas: state.oasisAreas,
          crystals: state.crystals,
          mutualAidEnergy: state.mutualAidEnergy,
          isBahasaMelayu: state.isBahasaMelayu,
          canRepair: state.canRepair,
          onRepair: state.repairOasisArea,
        ),
        const SizedBox(height: 4),
        _HomeMissionCard(
          mission: state.recommendedMission,
          isBahasaMelayu: state.isBahasaMelayu,
          onTap: () => _handleRecommendedMissionTap(context),
        ),
      ],
    );
  }

  void _handleRecommendedMissionTap(BuildContext context) {
    final mission = state.recommendedMission;
    final l10n = AppLocalizations.of(context)!;
    if (!mission.isReadyToClaim) {
      state.changeTab(1);
      return;
    }

    final claimed = state.claimRecommendedMissionReward();
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(
            claimed
                ? l10n.missionRewardClaimed(mission.rewardCrystals)
                : l10n.missionRewardAlreadyClaimed,
          ),
        ),
      );
  }

  void _toggleMissionReminders(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final nextValue = !state.missionReminders;
    state.updateMissionReminders(nextValue);
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(
            nextValue ? l10n.missionRemindersOn : l10n.missionRemindersOff,
          ),
        ),
      );
  }
}

class _HomeMissionCard extends StatelessWidget {
  const _HomeMissionCard({
    required this.mission,
    required this.isBahasaMelayu,
    required this.onTap,
  });

  final RecommendedMission mission;
  final bool isBahasaMelayu;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final topic = isBahasaMelayu ? mission.topicTitleBm : mission.topicTitle;
    final required = mission.requiredCompletions;
    final progress = required == 0 ? 0.0 : mission.visibleCompletions / required;
    final rewardLabel = mission.rewardClaimed
        ? l10n.rewardClaimedKeepPractising(topic)
        : mission.isReadyToClaim
            ? l10n.missionCompleteClaimReward
            : '+${mission.rewardCrystals} Crystals on completion';

    return MissionCard(
      topicLabel: topic,
      durationLabel: 'Easy - 5 min',
      title: l10n.completeTopicDrills(required, topic),
      rewardLabel: rewardLabel,
      progress: progress,
      progressLabel: '${mission.visibleCompletions}/$required',
      readyToClaim: mission.isReadyToClaim,
      onTap: onTap,
    );
  }
}
