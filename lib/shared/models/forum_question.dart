import 'package:cloud_firestore/cloud_firestore.dart';

class ForumQuestion {
  const ForumQuestion({
    required this.id,
    required this.authorId,
    required this.title,
    required this.text,
    this.createdAt,
    this.acceptedAnswerId,
    this.mode = 'free_form',
    this.sourceQuestionId,
    this.sourceContentVersion,
    this.prompt,
    this.promptBm,
    this.options = const [],
    this.optionsBm = const [],
  });

  final String id;
  final String authorId;
  final String title;
  final String text;
  final DateTime? createdAt;
  final String? acceptedAnswerId;
  final String mode;
  final String? sourceQuestionId;
  final String? sourceContentVersion;
  final String? prompt;
  final String? promptBm;
  final List<String> options;
  final List<String> optionsBm;

  factory ForumQuestion.fromFirestore(String id, Map<String, dynamic> data) {
    final snapshot = data['promptSnapshot'];
    final promptData = snapshot is Map<String, dynamic>
        ? snapshot
        : const <String, dynamic>{};
    return ForumQuestion(
      id: id,
      authorId: data['authorId'] as String? ?? '',
      title: data['title'] as String? ?? '',
      text: data['text'] as String? ?? '',
      createdAt: (data['createdAt'] as Timestamp?)?.toDate(),
      acceptedAnswerId: data['acceptedAnswerId'] as String?,
      mode: data['mode'] as String? ?? 'free_form',
      sourceQuestionId: data['sourceQuestionId'] as String?,
      sourceContentVersion: data['sourceContentVersion'] as String?,
      prompt: promptData['questionText'] as String? ?? data['text'] as String?,
      promptBm: promptData['questionTextBm'] as String?,
      options: (promptData['options'] as List?)
              ?.map((option) => option.toString())
              .toList(growable: false) ??
          const [],
      optionsBm: (promptData['optionsBm'] as List?)
              ?.map((option) => option.toString())
              .toList(growable: false) ??
          const [],
    );
  }

  /// Build the discussion page model from a server-owned linked-discussion
  /// projection returned by the create-or-open callable.
  factory ForumQuestion.fromLinkedDiscussion(LinkedDiscussion discussion) =>
      ForumQuestion(
        id: discussion.id,
        authorId: '',
        title: discussion.title ?? discussion.prompt,
        text: discussion.text ?? discussion.prompt,
        mode: 'linked',
        sourceQuestionId: discussion.sourceQuestionId,
        sourceContentVersion: discussion.sourceContentVersion,
        prompt: discussion.prompt,
        promptBm: discussion.promptBm,
        options: discussion.options,
        optionsBm: discussion.optionsBm,
      );
}

/// One deterministic page of forum questions plus an opaque cursor.
class ForumQuestionPage {
  const ForumQuestionPage({
    required this.questions,
    required this.nextCursor,
    required this.hasMore,
  });

  final List<ForumQuestion> questions;
  final String? nextCursor;
  final bool hasMore;
}

/// Server-owned canonical linked-discussion projection returned by the
/// ``openOrCreateForumDiscussion`` callable. The prompt/options snapshot is
/// client-safe; the answer key never leaves the server.
class LinkedDiscussion {
  const LinkedDiscussion({
    required this.id,
    required this.sourceQuestionId,
    required this.sourceContentVersion,
    this.prompt = '',
    this.promptBm,
    this.options = const [],
    this.optionsBm = const [],
    this.title,
    this.text,
    this.created = false,
  });

  final String id;
  final String sourceQuestionId;
  final String sourceContentVersion;
  final String prompt;
  final String? promptBm;
  final List<String> options;
  final List<String> optionsBm;
  final String? title;
  final String? text;
  final bool created;

  factory LinkedDiscussion.fromCallableResult(Map<String, dynamic> data) {
    final snapshot = data['promptSnapshot'];
    final promptData = snapshot is Map<String, dynamic>
        ? snapshot
        : const <String, dynamic>{};
    return LinkedDiscussion(
      id: data['discussionId'] as String? ?? '',
      sourceQuestionId: data['sourceQuestionId'] as String? ?? '',
      sourceContentVersion: data['sourceContentVersion'] as String? ?? '',
      prompt: promptData['questionText'] as String? ?? '',
      promptBm: promptData['questionTextBm'] as String?,
      options: (promptData['options'] as List?)
              ?.map((option) => option.toString())
              .toList(growable: false) ??
          const [],
      optionsBm: (promptData['optionsBm'] as List?)
              ?.map((option) => option.toString())
              .toList(growable: false) ??
          const [],
      title: data['title'] as String?,
      text: data['text'] as String?,
      created: data['created'] == true,
    );
  }
}
