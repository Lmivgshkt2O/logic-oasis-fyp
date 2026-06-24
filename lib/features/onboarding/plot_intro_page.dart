import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';

class PlotIntroPage extends StatefulWidget {
  const PlotIntroPage({super.key, required this.onFinished});

  final VoidCallback onFinished;

  @override
  State<PlotIntroPage> createState() => _PlotIntroPageState();
}

class _PlotIntroPageState extends State<PlotIntroPage> {
  final controller = PageController();
  int pageIndex = 0;

  final slides = const [
    _IntroSlide(
      icon: Icons.location_city_outlined,
      title: 'The oasis is waiting',
      body:
          'Logic Oasis was once a bright learning city, but its bridges, gardens and waterways have become quiet.',
    ),
    _IntroSlide(
      icon: Icons.calculate_outlined,
      title: 'Math restores each area',
      body:
          'Every practice mission earns Math Crystals that repair topic zones like Fraction Bridge and Decimal Waterway.',
    ),
    _IntroSlide(
      icon: Icons.handshake_outlined,
      title: 'Growth happens together',
      body:
          'Helping classmates creates Mutual Aid Energy. The oasis becomes stronger when students learn and explain together.',
    ),
  ];

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  void next() {
    if (pageIndex == slides.length - 1) {
      widget.onFinished();
      return;
    }
    controller.nextPage(
      duration: const Duration(milliseconds: 320),
      curve: Curves.easeOutCubic,
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Align(
              alignment: Alignment.centerRight,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 10, 20, 0),
                child: TextButton(
                  onPressed: widget.onFinished,
                  child: const Text('Skip'),
                ),
              ),
            ),
            Expanded(
              child: PageView.builder(
                controller: controller,
                onPageChanged: (index) {
                  setState(() {
                    pageIndex = index;
                  });
                },
                itemCount: slides.length,
                itemBuilder: (context, index) {
                  final slide = slides[index];
                  return Padding(
                    padding: const EdgeInsets.fromLTRB(24, 8, 24, 18),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        _IntroVisual(icon: slide.icon),
                        const SizedBox(height: 30),
                        Text(
                          slide.title,
                          style: theme.textTheme.headlineLarge,
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 12),
                        Text(
                          slide.body,
                          style: theme.textTheme.bodyLarge,
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      for (var i = 0; i < slides.length; i++)
                        AnimatedContainer(
                          duration: const Duration(milliseconds: 220),
                          width: i == pageIndex ? 24 : 8,
                          height: 8,
                          margin: const EdgeInsets.symmetric(horizontal: 4),
                          decoration: BoxDecoration(
                            color: i == pageIndex
                                ? LogicOasisTheme.leaf
                                : LogicOasisTheme.line,
                            borderRadius: BorderRadius.circular(99),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  FilledButton.icon(
                    onPressed: next,
                    icon: Icon(
                      pageIndex == slides.length - 1
                          ? Icons.spa
                          : Icons.arrow_forward,
                    ),
                    label: Text(
                      pageIndex == slides.length - 1
                          ? 'Enter Logic Oasis'
                          : 'Continue',
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _IntroSlide {
  const _IntroSlide({
    required this.icon,
    required this.title,
    required this.body,
  });

  final IconData icon;
  final String title;
  final String body;
}

class _IntroVisual extends StatelessWidget {
  const _IntroVisual({required this.icon});

  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 190,
      height: 190,
      decoration: BoxDecoration(
        color: LogicOasisTheme.sky,
        borderRadius: BorderRadius.circular(34),
        border: Border.all(color: LogicOasisTheme.line),
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          Positioned(
            bottom: 38,
            child: Container(
              width: 130,
              height: 34,
              decoration: BoxDecoration(
                color: LogicOasisTheme.water.withValues(alpha: 0.22),
                borderRadius: BorderRadius.circular(99),
              ),
            ),
          ),
          Container(
            width: 88,
            height: 88,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(22),
              border: Border.all(color: LogicOasisTheme.line),
            ),
            child: Icon(icon, size: 44, color: LogicOasisTheme.leaf),
          ),
        ],
      ),
    );
  }
}
