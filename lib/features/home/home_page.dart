import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/home/widgets/oasis_map.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/recommended_mission.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key, required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(17),
        child: Stack(
          children: [
            Positioned.fill(
              child: OasisMap(
                progress: state.restorationProgress,
                areas: state.oasisAreas,
                crystals: state.crystals,
                mutualAidEnergy: state.mutualAidEnergy,
                isBahasaMelayu: state.isBahasaMelayu,
                canRepair: state.canRepair,
                onRepair: state.repairOasisArea,
              ),
            ),
            Positioned(
              top: 18,
              right: 18,
              child: _NotificationButton(
                enabled: state.missionReminders,
                onTap: () {
                  final nextValue = !state.missionReminders;
                  state.updateMissionReminders(nextValue);
                  ScaffoldMessenger.of(context)
                    ..hideCurrentSnackBar()
                    ..showSnackBar(
                      SnackBar(
                        content: Text(
                          nextValue
                              ? l10n.missionRemindersOn
                              : l10n.missionRemindersOff,
                        ),
                      ),
                    );
                },
              ),
            ),
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              height: 128,
              child: IgnorePointer(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        Colors.transparent,
                        theme.scaffoldBackgroundColor.withValues(alpha: 0.42),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            Positioned(
              left: 14,
              right: 14,
              bottom: 18,
              child: _RecommendedMissionCard(
                mission: state.recommendedMission,
                isBahasaMelayu: state.isBahasaMelayu,
                onTap: () => _handleRecommendedMissionTap(context),
              ),
            ),
          ],
        ),
      ),
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
}

class _NotificationButton extends StatelessWidget {
  const _NotificationButton({required this.enabled, required this.onTap});

  final bool enabled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white.withValues(alpha: 0.76),
      shape: const CircleBorder(),
      child: InkWell(
        customBorder: const CircleBorder(),
        onTap: onTap,
        child: SizedBox(
          width: 46,
          height: 46,
          child: Icon(
            enabled
                ? Icons.notifications_none
                : Icons.notifications_off_outlined,
            color: LogicOasisTheme.ink,
          ),
        ),
      ),
    );
  }
}

class _RecommendedMissionCard extends StatelessWidget {
  const _RecommendedMissionCard({
    required this.mission,
    required this.isBahasaMelayu,
    required this.onTap,
  });

  final RecommendedMission mission;
  final bool isBahasaMelayu;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;
    final title = l10n.recommendedMission;
    final topicTitle = isBahasaMelayu
        ? mission.topicTitleBm
        : mission.topicTitle;
    final subtitle = _subtitle(topicTitle, l10n);
    final icon = mission.rewardClaimed
        ? Icons.check_circle_outline
        : mission.isReadyToClaim
        ? Icons.redeem_outlined
        : Icons.flag;
    final rewardText = mission.rewardClaimed
        ? l10n.done
        : '+${mission.rewardCrystals}';

    return Card(
      color: Colors.white.withValues(alpha: 0.92),
      elevation: 2,
      shadowColor: const Color(0x1A5C8069),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 13, 12, 13),
          child: Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: LogicOasisTheme.mint,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: LogicOasisTheme.leaf, size: 26),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      title,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontSize: 14.5,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 5),
                    Text(
                      subtitle,
                      style: theme.textTheme.bodyLarge?.copyWith(
                        color: LogicOasisTheme.ink,
                        fontSize: 13.5,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 6),
              const Icon(
                Icons.diamond_outlined,
                color: LogicOasisTheme.water,
                size: 19,
              ),
              const SizedBox(width: 2),
              Text(
                rewardText,
                style: theme.textTheme.titleMedium?.copyWith(fontSize: 14),
              ),
              const SizedBox(width: 5),
              Icon(
                mission.isReadyToClaim
                    ? Icons.touch_app_outlined
                    : Icons.chevron_right,
                size: 21,
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _subtitle(String topicTitle, AppLocalizations l10n) {
    final missionTopic = !isBahasaMelayu && topicTitle == 'Fractions'
        ? 'Fraction'
        : topicTitle;

    if (mission.rewardClaimed) {
      return l10n.rewardClaimedKeepPractising(topicTitle);
    }
    if (mission.isReadyToClaim) {
      return l10n.missionCompleteClaimReward;
    }
    return l10n.completeTopicDrills(
      mission.requiredCompletions,
      isBahasaMelayu ? topicTitle : missionTopic,
    );
  }
}
