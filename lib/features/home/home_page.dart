import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/home/widgets/oasis_map.dart';
import 'package:logic_oasis/shared/models/recommended_mission.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key, required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 8),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(18),
        child: Stack(
          children: [
            Positioned.fill(
              child: OasisMap(
                progress: state.restorationProgress,
                areas: state.oasisAreas,
                crystals: state.crystals,
                mutualAidEnergy: state.mutualAidEnergy,
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
                              ? state.t(
                                  'Mission reminders turned on',
                                  'Peringatan misi diaktifkan',
                                )
                              : state.t(
                                  'Mission reminders turned off',
                                  'Peringatan misi dimatikan',
                                ),
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
              left: 12,
              right: 12,
              bottom: 16,
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
                ? state.t(
                    'Mission reward claimed: +${mission.rewardCrystals} crystals',
                    'Ganjaran misi dituntut: +${mission.rewardCrystals} kristal',
                  )
                : state.t(
                    'Mission reward already claimed',
                    'Ganjaran misi sudah dituntut',
                  ),
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
    final title = isBahasaMelayu ? 'Misi dicadangkan' : 'Recommended mission';
    final topicTitle = isBahasaMelayu
        ? mission.topicTitleBm
        : mission.topicTitle;
    final subtitle = _subtitle(topicTitle);
    final icon = mission.rewardClaimed
        ? Icons.check_circle_outline
        : mission.isReadyToClaim
        ? Icons.redeem_outlined
        : Icons.flag;
    final rewardText = mission.rewardClaimed
        ? (isBahasaMelayu ? 'Selesai' : 'Done')
        : '+${mission.rewardCrystals}';

    return Card(
      color: Colors.white.withValues(alpha: 0.92),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(13),
          child: Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: LogicOasisTheme.mint,
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(icon, color: LogicOasisTheme.leaf),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      title,
                      style: theme.textTheme.titleMedium,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 5),
                    Text(
                      subtitle,
                      style: theme.textTheme.bodyLarge,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              const Icon(
                Icons.diamond_outlined,
                color: LogicOasisTheme.water,
                size: 20,
              ),
              const SizedBox(width: 3),
              Text(rewardText, style: theme.textTheme.titleMedium),
              const SizedBox(width: 6),
              Icon(
                mission.isReadyToClaim
                    ? Icons.touch_app_outlined
                    : Icons.chevron_right,
                size: 20,
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _subtitle(String topicTitle) {
    if (mission.rewardClaimed) {
      return isBahasaMelayu
          ? 'Ganjaran dituntut. Teruskan latihan $topicTitle.'
          : 'Reward claimed. Keep practising $topicTitle.';
    }
    if (mission.isReadyToClaim) {
      return isBahasaMelayu
          ? 'Misi selesai. Ketik untuk tuntut ganjaran.'
          : 'Mission complete. Tap to claim reward.';
    }
    return isBahasaMelayu
        ? 'Lengkapkan ${mission.requiredCompletions} latihan $topicTitle (${mission.visibleCompletions}/${mission.requiredCompletions})'
        : 'Complete ${mission.requiredCompletions} $topicTitle practices (${mission.visibleCompletions}/${mission.requiredCompletions})';
  }
}
