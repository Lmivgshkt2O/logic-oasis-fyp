import 'package:flutter/material.dart';

class LogicOasisDesign {
  const LogicOasisDesign._();

  static const forest = Color(0xFF0A5A3E);
  static const deepForest = Color(0xFF113B2D);
  static const ink = Color(0xFF17231F);
  static const body = Color(0xFF5A625D);
  static const mint = Color(0xFFCFF3D8);
  static const mintLight = Color(0xFFEFF9EC);
  static const page = Color(0xFFFFFAED);
  static const pageWarm = Color(0xFFFFF4DD);
  static const cream = Color(0xFFFFFDF3);
  static const card = Color(0xFFFFFDF8);
  static const line = Color(0xFFEDE7D9);
  static const yellow = Color(0xFFFFD33D);
  static const leaf = Color(0xFF37BD61);
  static const sky = Color(0xFFDDF5FF);
  static const coral = Color(0xFFFFE0D6);
  static const lavender = Color(0xFFF1E7FF);
  static const sand = Color(0xFFFFF0C8);
  static const water = Color(0xFF50D2D7);
  static const orange = Color(0xFFFF9D3B);
  static const purple = Color(0xFF7F70C8);

  static const screenPadding = EdgeInsets.fromLTRB(20, 20, 20, 24);
  static const radiusScreen = 30.0;
  static const radiusCard = 18.0;
  static const radiusLarge = 30.0;

  static List<BoxShadow> get softShadow => const [
    BoxShadow(
      color: Color(0x1F496F55),
      blurRadius: 24,
      offset: Offset(0, 10),
    ),
  ];

  static List<BoxShadow> get liftShadow => const [
    BoxShadow(
      color: Color(0x29496F55),
      blurRadius: 30,
      offset: Offset(0, 14),
    ),
  ];

  static TextStyle display(BuildContext context) {
    return Theme.of(context).textTheme.headlineLarge!.copyWith(
      color: forest,
      fontSize: 38,
      fontWeight: FontWeight.w900,
      height: 1.04,
    );
  }

  static TextStyle subtitle(BuildContext context) {
    return Theme.of(context).textTheme.bodyLarge!.copyWith(
      color: const Color(0xFF35443D),
      fontSize: 16,
      height: 1.18,
    );
  }

  static TextStyle title(BuildContext context) {
    return Theme.of(context).textTheme.titleMedium!.copyWith(
      color: deepForest,
      fontSize: 17,
      fontWeight: FontWeight.w900,
    );
  }
}

class FigmaPage extends StatelessWidget {
  const FigmaPage({
    super.key,
    required this.children,
    this.padding = LogicOasisDesign.screenPadding,
  });

  final List<Widget> children;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    return SizedBox.expand(
      child: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [LogicOasisDesign.page, LogicOasisDesign.pageWarm],
          ),
        ),
        child: SafeArea(
          bottom: false,
          child: SingleChildScrollView(
            padding: padding,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: children,
            ),
          ),
        ),
      ),
    );
  }
}

class FigmaHeader extends StatelessWidget {
  const FigmaHeader({
    super.key,
    required this.title,
    required this.subtitle,
    this.trailing,
  });

  final String title;
  final String subtitle;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: LogicOasisDesign.display(context)),
              const SizedBox(height: 7),
              Text(subtitle, style: LogicOasisDesign.subtitle(context)),
            ],
          ),
        ),
        if (trailing != null) ...[
          const SizedBox(width: 14),
          trailing!,
        ],
      ],
    );
  }
}

class FigmaCard extends StatelessWidget {
  const FigmaCard({
    super.key,
    required this.child,
    this.color = LogicOasisDesign.card,
    this.radius = LogicOasisDesign.radiusCard,
    this.padding = EdgeInsets.zero,
    this.onTap,
  });

  final Widget child;
  final Color color;
  final double radius;
  final EdgeInsets padding;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final content = Container(
      padding: padding,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: LogicOasisDesign.line),
        boxShadow: LogicOasisDesign.softShadow,
      ),
      child: child,
    );

    if (onTap == null) return content;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(radius),
        onTap: onTap,
        child: content,
      ),
    );
  }
}

class PointsBadge extends StatelessWidget {
  const PointsBadge({super.key, required this.value});

  final int value;

  @override
  Widget build(BuildContext context) {
    return FigmaCard(
      radius: 21,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.star_rounded, color: LogicOasisDesign.yellow, size: 23),
          const SizedBox(width: 4),
          Text(
            '$value',
            style: const TextStyle(
              color: LogicOasisDesign.ink,
              fontSize: 16,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class RoundIllustrationIcon extends StatelessWidget {
  const RoundIllustrationIcon({
    super.key,
    required this.icon,
    required this.color,
    this.size = 52,
    this.iconSize = 28,
  });

  final IconData icon;
  final Color color;
  final double size;
  final double iconSize;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color,
        boxShadow: LogicOasisDesign.softShadow,
      ),
      child: Icon(icon, color: Colors.white, size: iconSize),
    );
  }
}

class ProgressPill extends StatelessWidget {
  const ProgressPill({
    super.key,
    required this.value,
    this.height = 7,
    this.color = LogicOasisDesign.leaf,
  });

  final double value;
  final double height;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(99),
      child: LinearProgressIndicator(
        minHeight: height,
        value: value.clamp(0.0, 1.0).toDouble(),
        backgroundColor: const Color(0xFFE7E0D3),
        color: color,
      ),
    );
  }
}

class FigmaToyBlocks extends StatelessWidget {
  const FigmaToyBlocks({super.key, this.size = 76});

  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        children: [
          _block(4, size * .38, LogicOasisDesign.yellow),
          _block(size * .42, size * .47, const Color(0xFFFF784F)),
          _block(size * .44, size * .08, const Color(0xFF70BE54)),
          Positioned(
            top: 0,
            left: size * .53,
            child: Container(
              width: size * .3,
              height: size * .3,
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                color: Color(0xFF82CF52),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _block(double left, double top, Color color) {
    return Positioned(
      left: left,
      top: top,
      child: Container(
        width: size * .43,
        height: size * .36,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(10),
          boxShadow: LogicOasisDesign.softShadow,
        ),
      ),
    );
  }
}

class FigmaAbacusIcon extends StatelessWidget {
  const FigmaAbacusIcon({super.key, this.size = 76});

  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Container(
            width: size * .82,
            height: size * .7,
            decoration: BoxDecoration(
              color: const Color(0xFFD99A56),
              borderRadius: BorderRadius.circular(12),
              boxShadow: LogicOasisDesign.softShadow,
            ),
          ),
          for (var index = 0; index < 4; index += 1)
            Positioned(
              top: size * (.2 + index * .13),
              left: size * .18,
              right: size * .18,
              child: Container(height: 3, color: const Color(0xFFA96136)),
            ),
          for (var index = 0; index < 4; index += 1)
            Positioned(
              top: size * (.15 + index * .13),
              left: size * (.27 + index * .1),
              child: Container(
                width: size * .15,
                height: size * .15,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: [
                    const Color(0xFFE84E3E),
                    const Color(0xFFF3C23A),
                    const Color(0xFF67B957),
                    const Color(0xFF42A8D8),
                  ][index],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class FigmaNumberCubes extends StatelessWidget {
  const FigmaNumberCubes({super.key, this.size = 76});

  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        children: [
          _cube('1', 2, size * .43, const Color(0xFFF89A35)),
          _cube('3', size * .4, size * .47, const Color(0xFF3595C9)),
          _cube('2', size * .46, size * .12, const Color(0xFF68B95C)),
        ],
      ),
    );
  }

  Widget _cube(String label, double left, double top, Color color) {
    return Positioned(
      left: left,
      top: top,
      child: Container(
        width: size * .38,
        height: size * .34,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(10),
          boxShadow: LogicOasisDesign.softShadow,
        ),
        child: Text(
          label,
          style: TextStyle(
            color: Colors.white,
            fontSize: size * .26,
            fontWeight: FontWeight.w900,
          ),
        ),
      ),
    );
  }
}

class FigmaBoardGameIcon extends StatelessWidget {
  const FigmaBoardGameIcon({super.key, this.size = 76});

  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Container(
            width: size * .82,
            height: size * .56,
            decoration: BoxDecoration(
              color: const Color(0xFFDDB06C),
              borderRadius: BorderRadius.circular(12),
              boxShadow: LogicOasisDesign.softShadow,
            ),
          ),
          for (var index = 0; index < 4; index += 1)
            Positioned(
              left: size * (.24 + (index % 2) * .34),
              top: size * (.24 + (index ~/ 2) * .22),
              child: Container(
                width: size * .16,
                height: size * .16,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: [
                    const Color(0xFF49B6C9),
                    const Color(0xFFE36B4F),
                    const Color(0xFFE9A631),
                    const Color(0xFF379DC9),
                  ][index],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class FigmaBookIcon extends StatelessWidget {
  const FigmaBookIcon({super.key, this.size = 76});

  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Transform.rotate(
            angle: .08,
            child: Container(
              width: size * .74,
              height: size * .54,
              decoration: BoxDecoration(
                color: const Color(0xFFE75944),
                borderRadius: BorderRadius.circular(10),
                boxShadow: LogicOasisDesign.softShadow,
              ),
            ),
          ),
          Positioned(
            right: size * .08,
            child: Container(
              width: size * .37,
              height: size * .52,
              decoration: BoxDecoration(
                color: const Color(0xFFF5D7A4),
                borderRadius: BorderRadius.circular(8),
              ),
            ),
          ),
          Text(
            'A  B',
            style: TextStyle(
              color: LogicOasisDesign.forest,
              fontSize: size * .21,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class FigmaOasisScene extends StatelessWidget {
  const FigmaOasisScene({super.key});

  @override
  Widget build(BuildContext context) {
    return const CustomPaint(
      painter: const _FigmaOasisPainter(),
      child: const SizedBox.expand(),
    );
  }
}

class _FigmaOasisPainter extends CustomPainter {
  const _FigmaOasisPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final clip = RRect.fromRectAndRadius(
      rect,
      Radius.circular(size.width * .08),
    );
    canvas.clipRRect(clip);

    final bg = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [Color(0xFFE6FAD8), Color(0xFFC4F2DD)],
      ).createShader(rect);
    canvas.drawRRect(clip, bg);

    _shadow(canvas, Offset(size.width * .51, size.height * .7), size.width * .66, size.height * .11);
    _oval(canvas, Offset(size.width * .49, size.height * .61), size.width * .72, size.height * .44, const Color(0xFF80C75A));
    _oval(canvas, Offset(size.width * .46, size.height * .66), size.width * .42, size.height * .28, LogicOasisDesign.water);
    _waterfall(canvas, size);
    _house(canvas, size);
    _tree(canvas, Offset(size.width * .25, size.height * .46), size.width * .08, const Color(0xFFFFB8CC));
    _tree(canvas, Offset(size.width * .82, size.height * .39), size.width * .12, const Color(0xFF8BDD63));
    _tree(canvas, Offset(size.width * .72, size.height * .31), size.width * .09, const Color(0xFF9BE66A));
    _dock(canvas, size);
    _duck(canvas, size);
    _stones(canvas, size);
    _plant(canvas, Offset(size.width * .88, size.height * .74), size.width * .04);
    _plant(canvas, Offset(size.width * .14, size.height * .63), size.width * .035);
  }

  void _waterfall(Canvas canvas, Size size) {
    final paint = Paint()..color = const Color(0xFF5AD6E6);
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(size.width * .18, size.height * .36, size.width * .14, size.height * .28),
        Radius.circular(size.width * .06),
      ),
      paint,
    );
    canvas.drawLine(
      Offset(size.width * .22, size.height * .39),
      Offset(size.width * .22, size.height * .57),
      Paint()
        ..color = Colors.white.withValues(alpha: .45)
        ..strokeWidth = 3
        ..strokeCap = StrokeCap.round,
    );
  }

  void _house(Canvas canvas, Size size) {
    final body = Rect.fromLTWH(size.width * .56, size.height * .36, size.width * .18, size.height * .2);
    _shadow(canvas, body.center + Offset(0, size.height * .05), size.width * .2, size.height * .05);
    canvas.drawRRect(
      RRect.fromRectAndRadius(body, Radius.circular(size.width * .025)),
      Paint()..color = const Color(0xFFD9A653),
    );
    final roof = Path()
      ..moveTo(size.width * .52, size.height * .38)
      ..lineTo(size.width * .65, size.height * .24)
      ..lineTo(size.width * .78, size.height * .38)
      ..close();
    canvas.drawPath(roof, Paint()..color = const Color(0xFF347F67));
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(size.width * .62, size.height * .45, size.width * .06, size.height * .11),
        Radius.circular(size.width * .025),
      ),
      Paint()..color = const Color(0xFF8B5A32),
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(size.width * .55, size.height * .56, size.width * .22, size.height * .04),
        Radius.circular(size.width * .02),
      ),
      Paint()..color = const Color(0xFFC58A49),
    );
  }

  void _tree(Canvas canvas, Offset base, double scale, Color crown) {
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromCenter(center: base + Offset(0, scale * 1.35), width: scale * .45, height: scale * 2),
        Radius.circular(scale * .22),
      ),
      Paint()..color = const Color(0xFF9A6339),
    );
    _oval(canvas, base + Offset(-scale * .55, 0), scale * 1.4, scale * 1.25, crown);
    _oval(canvas, base + Offset(scale * .35, -scale * .1), scale * 1.35, scale * 1.2, Color.alphaBlend(Colors.white.withValues(alpha: .08), crown));
    _oval(canvas, base + Offset(0, -scale * .65), scale * 1.15, scale * 1.25, Color.alphaBlend(Colors.white.withValues(alpha: .15), crown));
  }

  void _dock(Canvas canvas, Size size) {
    final paint = Paint()..color = const Color(0xFFB77B3D);
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(size.width * .71, size.height * .71, size.width * .2, size.height * .045),
        Radius.circular(size.width * .02),
      ),
      paint,
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(size.width * .74, size.height * .66, size.width * .025, size.height * .14),
        Radius.circular(size.width * .012),
      ),
      paint,
    );
  }

  void _duck(Canvas canvas, Size size) {
    _oval(canvas, Offset(size.width * .39, size.height * .65), size.width * .075, size.height * .045, LogicOasisDesign.yellow);
    _oval(canvas, Offset(size.width * .43, size.height * .62), size.width * .04, size.height * .04, LogicOasisDesign.yellow);
  }

  void _stones(Canvas canvas, Size size) {
    for (var index = 0; index < 5; index += 1) {
      _oval(
        canvas,
        Offset(size.width * (.58 + index * .075), size.height * (.66 + (index % 2) * .04)),
        size.width * .06,
        size.height * .032,
        const Color(0xFFDAE3D1),
      );
    }
  }

  void _plant(Canvas canvas, Offset base, double scale) {
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromCenter(center: base + Offset(0, scale * 1.3), width: scale * 1.4, height: scale * .9),
        Radius.circular(scale * .4),
      ),
      Paint()..color = const Color(0xFFCE8840),
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromCenter(center: base, width: scale * .22, height: scale * 1.4),
        Radius.circular(scale * .1),
      ),
      Paint()..color = const Color(0xFF2C8E4B),
    );
    _oval(canvas, base + Offset(-scale * .45, -scale * .2), scale, scale * .56, const Color(0xFF66C75C));
    _oval(canvas, base + Offset(scale * .45, -scale * .45), scale, scale * .62, const Color(0xFF77D85F));
  }

  void _oval(Canvas canvas, Offset center, double width, double height, Color color) {
    canvas.drawOval(
      Rect.fromCenter(center: center, width: width, height: height),
      Paint()..color = color,
    );
  }

  void _shadow(Canvas canvas, Offset center, double width, double height) {
    canvas.drawOval(
      Rect.fromCenter(center: center, width: width, height: height),
      Paint()..color = const Color(0x220B3D2E),
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
