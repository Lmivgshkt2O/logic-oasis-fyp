import 'package:cloud_functions/cloud_functions.dart';
import 'package:logic_oasis/shared/models/linked_child_context.dart';

abstract class ParentLinkedChildrenGateway {
  Future<List<LinkedChildContext>> loadLinkedChildren();
}

class ParentLinkContextException implements Exception {
  const ParentLinkContextException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// The sole Flutter boundary for resolving a parent's active linked children.
class ParentLinkedChildrenService implements ParentLinkedChildrenGateway {
  ParentLinkedChildrenService({FirebaseFunctions? functions})
    : _functions =
          functions ?? FirebaseFunctions.instanceFor(region: 'asia-southeast1');

  final FirebaseFunctions _functions;

  @override
  Future<List<LinkedChildContext>> loadLinkedChildren() async {
    try {
      final result = await _functions
          .httpsCallable('getLinkedChildren')
          .call<Map<Object?, Object?>>(<String, Object>{});
      final rawChildren = result.data['children'];
      if (rawChildren is! List) {
        throw const ParentLinkContextException(
          'Linked learner context is unavailable.',
        );
      }
      final children =
          rawChildren
              .whereType<Map>()
              .map(
                (item) => LinkedChildContext.fromCallableData(
                  Map<Object?, Object?>.from(item),
                ),
              )
              .toList(growable: false)
            ..sort((a, b) => a.displayName.compareTo(b.displayName));
      return children;
    } on FirebaseFunctionsException catch (error) {
      throw ParentLinkContextException(
        error.message ?? 'Unable to load linked learner updates.',
      );
    } on FormatException {
      throw const ParentLinkContextException(
        'Linked learner context is invalid.',
      );
    }
  }
}
