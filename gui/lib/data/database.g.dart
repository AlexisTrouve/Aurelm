// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'database.dart';

// ignore_for_file: type=lint
class $CivCivilizationsTable extends CivCivilizations
    with TableInfo<$CivCivilizationsTable, CivRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $CivCivilizationsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
      'id', aliasedName, false,
      hasAutoIncrement: true,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('PRIMARY KEY AUTOINCREMENT'));
  static const VerificationMeta _nameMeta = const VerificationMeta('name');
  @override
  late final GeneratedColumn<String> name = GeneratedColumn<String>(
      'name', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: true,
      defaultConstraints: GeneratedColumn.constraintIsAlways('UNIQUE'));
  static const VerificationMeta _playerNameMeta =
      const VerificationMeta('playerName');
  @override
  late final GeneratedColumn<String> playerName = GeneratedColumn<String>(
      'player_name', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _discordChannelIdMeta =
      const VerificationMeta('discordChannelId');
  @override
  late final GeneratedColumn<String> discordChannelId = GeneratedColumn<String>(
      'discord_channel_id', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _createdAtMeta =
      const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
      'created_at', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _updatedAtMeta =
      const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<String> updatedAt = GeneratedColumn<String>(
      'updated_at', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  @override
  List<GeneratedColumn> get $columns =>
      [id, name, playerName, discordChannelId, createdAt, updatedAt];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'civ_civilizations';
  @override
  VerificationContext validateIntegrity(Insertable<CivRow> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('name')) {
      context.handle(
          _nameMeta, name.isAcceptableOrUnknown(data['name']!, _nameMeta));
    } else if (isInserting) {
      context.missing(_nameMeta);
    }
    if (data.containsKey('player_name')) {
      context.handle(
          _playerNameMeta,
          playerName.isAcceptableOrUnknown(
              data['player_name']!, _playerNameMeta));
    }
    if (data.containsKey('discord_channel_id')) {
      context.handle(
          _discordChannelIdMeta,
          discordChannelId.isAcceptableOrUnknown(
              data['discord_channel_id']!, _discordChannelIdMeta));
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta,
          createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta,
          updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  CivRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return CivRow(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}id'])!,
      name: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}name'])!,
      playerName: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}player_name']),
      discordChannelId: attachedDatabase.typeMapping.read(
          DriftSqlType.string, data['${effectivePrefix}discord_channel_id']),
      createdAt: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}created_at'])!,
      updatedAt: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}updated_at'])!,
    );
  }

  @override
  $CivCivilizationsTable createAlias(String alias) {
    return $CivCivilizationsTable(attachedDatabase, alias);
  }
}

class CivRow extends DataClass implements Insertable<CivRow> {
  final int id;
  final String name;
  final String? playerName;
  final String? discordChannelId;
  final String createdAt;
  final String updatedAt;
  const CivRow(
      {required this.id,
      required this.name,
      this.playerName,
      this.discordChannelId,
      required this.createdAt,
      required this.updatedAt});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['name'] = Variable<String>(name);
    if (!nullToAbsent || playerName != null) {
      map['player_name'] = Variable<String>(playerName);
    }
    if (!nullToAbsent || discordChannelId != null) {
      map['discord_channel_id'] = Variable<String>(discordChannelId);
    }
    map['created_at'] = Variable<String>(createdAt);
    map['updated_at'] = Variable<String>(updatedAt);
    return map;
  }

  CivCivilizationsCompanion toCompanion(bool nullToAbsent) {
    return CivCivilizationsCompanion(
      id: Value(id),
      name: Value(name),
      playerName: playerName == null && nullToAbsent
          ? const Value.absent()
          : Value(playerName),
      discordChannelId: discordChannelId == null && nullToAbsent
          ? const Value.absent()
          : Value(discordChannelId),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
    );
  }

  factory CivRow.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return CivRow(
      id: serializer.fromJson<int>(json['id']),
      name: serializer.fromJson<String>(json['name']),
      playerName: serializer.fromJson<String?>(json['playerName']),
      discordChannelId: serializer.fromJson<String?>(json['discordChannelId']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
      updatedAt: serializer.fromJson<String>(json['updatedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'name': serializer.toJson<String>(name),
      'playerName': serializer.toJson<String?>(playerName),
      'discordChannelId': serializer.toJson<String?>(discordChannelId),
      'createdAt': serializer.toJson<String>(createdAt),
      'updatedAt': serializer.toJson<String>(updatedAt),
    };
  }

  CivRow copyWith(
          {int? id,
          String? name,
          Value<String?> playerName = const Value.absent(),
          Value<String?> discordChannelId = const Value.absent(),
          String? createdAt,
          String? updatedAt}) =>
      CivRow(
        id: id ?? this.id,
        name: name ?? this.name,
        playerName: playerName.present ? playerName.value : this.playerName,
        discordChannelId: discordChannelId.present
            ? discordChannelId.value
            : this.discordChannelId,
        createdAt: createdAt ?? this.createdAt,
        updatedAt: updatedAt ?? this.updatedAt,
      );
  CivRow copyWithCompanion(CivCivilizationsCompanion data) {
    return CivRow(
      id: data.id.present ? data.id.value : this.id,
      name: data.name.present ? data.name.value : this.name,
      playerName:
          data.playerName.present ? data.playerName.value : this.playerName,
      discordChannelId: data.discordChannelId.present
          ? data.discordChannelId.value
          : this.discordChannelId,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('CivRow(')
          ..write('id: $id, ')
          ..write('name: $name, ')
          ..write('playerName: $playerName, ')
          ..write('discordChannelId: $discordChannelId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode =>
      Object.hash(id, name, playerName, discordChannelId, createdAt, updatedAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is CivRow &&
          other.id == this.id &&
          other.name == this.name &&
          other.playerName == this.playerName &&
          other.discordChannelId == this.discordChannelId &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt);
}

class CivCivilizationsCompanion extends UpdateCompanion<CivRow> {
  final Value<int> id;
  final Value<String> name;
  final Value<String?> playerName;
  final Value<String?> discordChannelId;
  final Value<String> createdAt;
  final Value<String> updatedAt;
  const CivCivilizationsCompanion({
    this.id = const Value.absent(),
    this.name = const Value.absent(),
    this.playerName = const Value.absent(),
    this.discordChannelId = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
  });
  CivCivilizationsCompanion.insert({
    this.id = const Value.absent(),
    required String name,
    this.playerName = const Value.absent(),
    this.discordChannelId = const Value.absent(),
    required String createdAt,
    required String updatedAt,
  })  : name = Value(name),
        createdAt = Value(createdAt),
        updatedAt = Value(updatedAt);
  static Insertable<CivRow> custom({
    Expression<int>? id,
    Expression<String>? name,
    Expression<String>? playerName,
    Expression<String>? discordChannelId,
    Expression<String>? createdAt,
    Expression<String>? updatedAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (name != null) 'name': name,
      if (playerName != null) 'player_name': playerName,
      if (discordChannelId != null) 'discord_channel_id': discordChannelId,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
    });
  }

  CivCivilizationsCompanion copyWith(
      {Value<int>? id,
      Value<String>? name,
      Value<String?>? playerName,
      Value<String?>? discordChannelId,
      Value<String>? createdAt,
      Value<String>? updatedAt}) {
    return CivCivilizationsCompanion(
      id: id ?? this.id,
      name: name ?? this.name,
      playerName: playerName ?? this.playerName,
      discordChannelId: discordChannelId ?? this.discordChannelId,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (name.present) {
      map['name'] = Variable<String>(name.value);
    }
    if (playerName.present) {
      map['player_name'] = Variable<String>(playerName.value);
    }
    if (discordChannelId.present) {
      map['discord_channel_id'] = Variable<String>(discordChannelId.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<String>(updatedAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('CivCivilizationsCompanion(')
          ..write('id: $id, ')
          ..write('name: $name, ')
          ..write('playerName: $playerName, ')
          ..write('discordChannelId: $discordChannelId, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }
}

class $TurnTurnsTable extends TurnTurns
    with TableInfo<$TurnTurnsTable, TurnRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $TurnTurnsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
      'id', aliasedName, false,
      hasAutoIncrement: true,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('PRIMARY KEY AUTOINCREMENT'));
  static const VerificationMeta _civIdMeta = const VerificationMeta('civId');
  @override
  late final GeneratedColumn<int> civId = GeneratedColumn<int>(
      'civ_id', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _turnNumberMeta =
      const VerificationMeta('turnNumber');
  @override
  late final GeneratedColumn<int> turnNumber = GeneratedColumn<int>(
      'turn_number', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _titleMeta = const VerificationMeta('title');
  @override
  late final GeneratedColumn<String> title = GeneratedColumn<String>(
      'title', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _summaryMeta =
      const VerificationMeta('summary');
  @override
  late final GeneratedColumn<String> summary = GeneratedColumn<String>(
      'summary', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _detailedSummaryMeta =
      const VerificationMeta('detailedSummary');
  @override
  late final GeneratedColumn<String> detailedSummary = GeneratedColumn<String>(
      'detailed_summary', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _rawMessageIdsMeta =
      const VerificationMeta('rawMessageIds');
  @override
  late final GeneratedColumn<String> rawMessageIds = GeneratedColumn<String>(
      'raw_message_ids', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _turnTypeMeta =
      const VerificationMeta('turnType');
  @override
  late final GeneratedColumn<String> turnType = GeneratedColumn<String>(
      'turn_type', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('standard'));
  static const VerificationMeta _gameDateStartMeta =
      const VerificationMeta('gameDateStart');
  @override
  late final GeneratedColumn<String> gameDateStart = GeneratedColumn<String>(
      'game_date_start', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _gameDateEndMeta =
      const VerificationMeta('gameDateEnd');
  @override
  late final GeneratedColumn<String> gameDateEnd = GeneratedColumn<String>(
      'game_date_end', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _createdAtMeta =
      const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
      'created_at', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _processedAtMeta =
      const VerificationMeta('processedAt');
  @override
  late final GeneratedColumn<String> processedAt = GeneratedColumn<String>(
      'processed_at', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _thematicTagsMeta =
      const VerificationMeta('thematicTags');
  @override
  late final GeneratedColumn<String> thematicTags = GeneratedColumn<String>(
      'thematic_tags', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _technologiesMeta =
      const VerificationMeta('technologies');
  @override
  late final GeneratedColumn<String> technologies = GeneratedColumn<String>(
      'technologies', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _resourcesMeta =
      const VerificationMeta('resources');
  @override
  late final GeneratedColumn<String> resources = GeneratedColumn<String>(
      'resources', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _beliefsMeta =
      const VerificationMeta('beliefs');
  @override
  late final GeneratedColumn<String> beliefs = GeneratedColumn<String>(
      'beliefs', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _geographyMeta =
      const VerificationMeta('geography');
  @override
  late final GeneratedColumn<String> geography = GeneratedColumn<String>(
      'geography', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _keyEventsMeta =
      const VerificationMeta('keyEvents');
  @override
  late final GeneratedColumn<String> keyEvents = GeneratedColumn<String>(
      'key_events', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _choicesMadeMeta =
      const VerificationMeta('choicesMade');
  @override
  late final GeneratedColumn<String> choicesMade = GeneratedColumn<String>(
      'choices_made', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _choicesProposedMeta =
      const VerificationMeta('choicesProposed');
  @override
  late final GeneratedColumn<String> choicesProposed = GeneratedColumn<String>(
      'choices_proposed', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _techEraMeta =
      const VerificationMeta('techEra');
  @override
  late final GeneratedColumn<String> techEra = GeneratedColumn<String>(
      'tech_era', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _fantasyLevelMeta =
      const VerificationMeta('fantasyLevel');
  @override
  late final GeneratedColumn<String> fantasyLevel = GeneratedColumn<String>(
      'fantasy_level', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _noveltySummaryMeta =
      const VerificationMeta('noveltySummary');
  @override
  late final GeneratedColumn<String> noveltySummary = GeneratedColumn<String>(
      'novelty_summary', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _newEntityIdsMeta =
      const VerificationMeta('newEntityIds');
  @override
  late final GeneratedColumn<String> newEntityIds = GeneratedColumn<String>(
      'new_entity_ids', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _playerStrategyMeta =
      const VerificationMeta('playerStrategy');
  @override
  late final GeneratedColumn<String> playerStrategy = GeneratedColumn<String>(
      'player_strategy', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _strategyTagsMeta =
      const VerificationMeta('strategyTags');
  @override
  late final GeneratedColumn<String> strategyTags = GeneratedColumn<String>(
      'strategy_tags', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  @override
  List<GeneratedColumn> get $columns => [
        id,
        civId,
        turnNumber,
        title,
        summary,
        detailedSummary,
        rawMessageIds,
        turnType,
        gameDateStart,
        gameDateEnd,
        createdAt,
        processedAt,
        thematicTags,
        technologies,
        resources,
        beliefs,
        geography,
        keyEvents,
        choicesMade,
        choicesProposed,
        techEra,
        fantasyLevel,
        noveltySummary,
        newEntityIds,
        playerStrategy,
        strategyTags
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'turn_turns';
  @override
  VerificationContext validateIntegrity(Insertable<TurnRow> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('civ_id')) {
      context.handle(
          _civIdMeta, civId.isAcceptableOrUnknown(data['civ_id']!, _civIdMeta));
    } else if (isInserting) {
      context.missing(_civIdMeta);
    }
    if (data.containsKey('turn_number')) {
      context.handle(
          _turnNumberMeta,
          turnNumber.isAcceptableOrUnknown(
              data['turn_number']!, _turnNumberMeta));
    } else if (isInserting) {
      context.missing(_turnNumberMeta);
    }
    if (data.containsKey('title')) {
      context.handle(
          _titleMeta, title.isAcceptableOrUnknown(data['title']!, _titleMeta));
    }
    if (data.containsKey('summary')) {
      context.handle(_summaryMeta,
          summary.isAcceptableOrUnknown(data['summary']!, _summaryMeta));
    }
    if (data.containsKey('detailed_summary')) {
      context.handle(
          _detailedSummaryMeta,
          detailedSummary.isAcceptableOrUnknown(
              data['detailed_summary']!, _detailedSummaryMeta));
    }
    if (data.containsKey('raw_message_ids')) {
      context.handle(
          _rawMessageIdsMeta,
          rawMessageIds.isAcceptableOrUnknown(
              data['raw_message_ids']!, _rawMessageIdsMeta));
    } else if (isInserting) {
      context.missing(_rawMessageIdsMeta);
    }
    if (data.containsKey('turn_type')) {
      context.handle(_turnTypeMeta,
          turnType.isAcceptableOrUnknown(data['turn_type']!, _turnTypeMeta));
    }
    if (data.containsKey('game_date_start')) {
      context.handle(
          _gameDateStartMeta,
          gameDateStart.isAcceptableOrUnknown(
              data['game_date_start']!, _gameDateStartMeta));
    }
    if (data.containsKey('game_date_end')) {
      context.handle(
          _gameDateEndMeta,
          gameDateEnd.isAcceptableOrUnknown(
              data['game_date_end']!, _gameDateEndMeta));
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta,
          createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('processed_at')) {
      context.handle(
          _processedAtMeta,
          processedAt.isAcceptableOrUnknown(
              data['processed_at']!, _processedAtMeta));
    }
    if (data.containsKey('thematic_tags')) {
      context.handle(
          _thematicTagsMeta,
          thematicTags.isAcceptableOrUnknown(
              data['thematic_tags']!, _thematicTagsMeta));
    }
    if (data.containsKey('technologies')) {
      context.handle(
          _technologiesMeta,
          technologies.isAcceptableOrUnknown(
              data['technologies']!, _technologiesMeta));
    }
    if (data.containsKey('resources')) {
      context.handle(_resourcesMeta,
          resources.isAcceptableOrUnknown(data['resources']!, _resourcesMeta));
    }
    if (data.containsKey('beliefs')) {
      context.handle(_beliefsMeta,
          beliefs.isAcceptableOrUnknown(data['beliefs']!, _beliefsMeta));
    }
    if (data.containsKey('geography')) {
      context.handle(_geographyMeta,
          geography.isAcceptableOrUnknown(data['geography']!, _geographyMeta));
    }
    if (data.containsKey('key_events')) {
      context.handle(_keyEventsMeta,
          keyEvents.isAcceptableOrUnknown(data['key_events']!, _keyEventsMeta));
    }
    if (data.containsKey('choices_made')) {
      context.handle(
          _choicesMadeMeta,
          choicesMade.isAcceptableOrUnknown(
              data['choices_made']!, _choicesMadeMeta));
    }
    if (data.containsKey('choices_proposed')) {
      context.handle(
          _choicesProposedMeta,
          choicesProposed.isAcceptableOrUnknown(
              data['choices_proposed']!, _choicesProposedMeta));
    }
    if (data.containsKey('tech_era')) {
      context.handle(_techEraMeta,
          techEra.isAcceptableOrUnknown(data['tech_era']!, _techEraMeta));
    }
    if (data.containsKey('fantasy_level')) {
      context.handle(
          _fantasyLevelMeta,
          fantasyLevel.isAcceptableOrUnknown(
              data['fantasy_level']!, _fantasyLevelMeta));
    }
    if (data.containsKey('novelty_summary')) {
      context.handle(
          _noveltySummaryMeta,
          noveltySummary.isAcceptableOrUnknown(
              data['novelty_summary']!, _noveltySummaryMeta));
    }
    if (data.containsKey('new_entity_ids')) {
      context.handle(
          _newEntityIdsMeta,
          newEntityIds.isAcceptableOrUnknown(
              data['new_entity_ids']!, _newEntityIdsMeta));
    }
    if (data.containsKey('player_strategy')) {
      context.handle(
          _playerStrategyMeta,
          playerStrategy.isAcceptableOrUnknown(
              data['player_strategy']!, _playerStrategyMeta));
    }
    if (data.containsKey('strategy_tags')) {
      context.handle(
          _strategyTagsMeta,
          strategyTags.isAcceptableOrUnknown(
              data['strategy_tags']!, _strategyTagsMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  TurnRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return TurnRow(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}id'])!,
      civId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}civ_id'])!,
      turnNumber: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}turn_number'])!,
      title: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}title']),
      summary: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}summary']),
      detailedSummary: attachedDatabase.typeMapping.read(
          DriftSqlType.string, data['${effectivePrefix}detailed_summary']),
      rawMessageIds: attachedDatabase.typeMapping.read(
          DriftSqlType.string, data['${effectivePrefix}raw_message_ids'])!,
      turnType: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}turn_type'])!,
      gameDateStart: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}game_date_start']),
      gameDateEnd: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}game_date_end']),
      createdAt: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}created_at'])!,
      processedAt: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}processed_at']),
      thematicTags: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}thematic_tags']),
      technologies: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}technologies']),
      resources: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}resources']),
      beliefs: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}beliefs']),
      geography: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}geography']),
      keyEvents: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}key_events']),
      choicesMade: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}choices_made']),
      choicesProposed: attachedDatabase.typeMapping.read(
          DriftSqlType.string, data['${effectivePrefix}choices_proposed']),
      techEra: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}tech_era']),
      fantasyLevel: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}fantasy_level']),
      noveltySummary: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}novelty_summary']),
      newEntityIds: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}new_entity_ids']),
      playerStrategy: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}player_strategy']),
      strategyTags: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}strategy_tags']),
    );
  }

  @override
  $TurnTurnsTable createAlias(String alias) {
    return $TurnTurnsTable(attachedDatabase, alias);
  }
}

class TurnRow extends DataClass implements Insertable<TurnRow> {
  final int id;
  final int civId;
  final int turnNumber;
  final String? title;
  final String? summary;
  final String? detailedSummary;
  final String rawMessageIds;
  final String turnType;
  final String? gameDateStart;
  final String? gameDateEnd;
  final String createdAt;
  final String? processedAt;
  final String? thematicTags;
  final String? technologies;
  final String? resources;
  final String? beliefs;
  final String? geography;
  final String? keyEvents;
  final String? choicesMade;
  final String? choicesProposed;
  final String? techEra;
  final String? fantasyLevel;
  final String? noveltySummary;
  final String? newEntityIds;
  final String? playerStrategy;
  final String? strategyTags;
  const TurnRow(
      {required this.id,
      required this.civId,
      required this.turnNumber,
      this.title,
      this.summary,
      this.detailedSummary,
      required this.rawMessageIds,
      required this.turnType,
      this.gameDateStart,
      this.gameDateEnd,
      required this.createdAt,
      this.processedAt,
      this.thematicTags,
      this.technologies,
      this.resources,
      this.beliefs,
      this.geography,
      this.keyEvents,
      this.choicesMade,
      this.choicesProposed,
      this.techEra,
      this.fantasyLevel,
      this.noveltySummary,
      this.newEntityIds,
      this.playerStrategy,
      this.strategyTags});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['civ_id'] = Variable<int>(civId);
    map['turn_number'] = Variable<int>(turnNumber);
    if (!nullToAbsent || title != null) {
      map['title'] = Variable<String>(title);
    }
    if (!nullToAbsent || summary != null) {
      map['summary'] = Variable<String>(summary);
    }
    if (!nullToAbsent || detailedSummary != null) {
      map['detailed_summary'] = Variable<String>(detailedSummary);
    }
    map['raw_message_ids'] = Variable<String>(rawMessageIds);
    map['turn_type'] = Variable<String>(turnType);
    if (!nullToAbsent || gameDateStart != null) {
      map['game_date_start'] = Variable<String>(gameDateStart);
    }
    if (!nullToAbsent || gameDateEnd != null) {
      map['game_date_end'] = Variable<String>(gameDateEnd);
    }
    map['created_at'] = Variable<String>(createdAt);
    if (!nullToAbsent || processedAt != null) {
      map['processed_at'] = Variable<String>(processedAt);
    }
    if (!nullToAbsent || thematicTags != null) {
      map['thematic_tags'] = Variable<String>(thematicTags);
    }
    if (!nullToAbsent || technologies != null) {
      map['technologies'] = Variable<String>(technologies);
    }
    if (!nullToAbsent || resources != null) {
      map['resources'] = Variable<String>(resources);
    }
    if (!nullToAbsent || beliefs != null) {
      map['beliefs'] = Variable<String>(beliefs);
    }
    if (!nullToAbsent || geography != null) {
      map['geography'] = Variable<String>(geography);
    }
    if (!nullToAbsent || keyEvents != null) {
      map['key_events'] = Variable<String>(keyEvents);
    }
    if (!nullToAbsent || choicesMade != null) {
      map['choices_made'] = Variable<String>(choicesMade);
    }
    if (!nullToAbsent || choicesProposed != null) {
      map['choices_proposed'] = Variable<String>(choicesProposed);
    }
    if (!nullToAbsent || techEra != null) {
      map['tech_era'] = Variable<String>(techEra);
    }
    if (!nullToAbsent || fantasyLevel != null) {
      map['fantasy_level'] = Variable<String>(fantasyLevel);
    }
    if (!nullToAbsent || noveltySummary != null) {
      map['novelty_summary'] = Variable<String>(noveltySummary);
    }
    if (!nullToAbsent || newEntityIds != null) {
      map['new_entity_ids'] = Variable<String>(newEntityIds);
    }
    if (!nullToAbsent || playerStrategy != null) {
      map['player_strategy'] = Variable<String>(playerStrategy);
    }
    if (!nullToAbsent || strategyTags != null) {
      map['strategy_tags'] = Variable<String>(strategyTags);
    }
    return map;
  }

  TurnTurnsCompanion toCompanion(bool nullToAbsent) {
    return TurnTurnsCompanion(
      id: Value(id),
      civId: Value(civId),
      turnNumber: Value(turnNumber),
      title:
          title == null && nullToAbsent ? const Value.absent() : Value(title),
      summary: summary == null && nullToAbsent
          ? const Value.absent()
          : Value(summary),
      detailedSummary: detailedSummary == null && nullToAbsent
          ? const Value.absent()
          : Value(detailedSummary),
      rawMessageIds: Value(rawMessageIds),
      turnType: Value(turnType),
      gameDateStart: gameDateStart == null && nullToAbsent
          ? const Value.absent()
          : Value(gameDateStart),
      gameDateEnd: gameDateEnd == null && nullToAbsent
          ? const Value.absent()
          : Value(gameDateEnd),
      createdAt: Value(createdAt),
      processedAt: processedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(processedAt),
      thematicTags: thematicTags == null && nullToAbsent
          ? const Value.absent()
          : Value(thematicTags),
      technologies: technologies == null && nullToAbsent
          ? const Value.absent()
          : Value(technologies),
      resources: resources == null && nullToAbsent
          ? const Value.absent()
          : Value(resources),
      beliefs: beliefs == null && nullToAbsent
          ? const Value.absent()
          : Value(beliefs),
      geography: geography == null && nullToAbsent
          ? const Value.absent()
          : Value(geography),
      keyEvents: keyEvents == null && nullToAbsent
          ? const Value.absent()
          : Value(keyEvents),
      choicesMade: choicesMade == null && nullToAbsent
          ? const Value.absent()
          : Value(choicesMade),
      choicesProposed: choicesProposed == null && nullToAbsent
          ? const Value.absent()
          : Value(choicesProposed),
      techEra: techEra == null && nullToAbsent
          ? const Value.absent()
          : Value(techEra),
      fantasyLevel: fantasyLevel == null && nullToAbsent
          ? const Value.absent()
          : Value(fantasyLevel),
      noveltySummary: noveltySummary == null && nullToAbsent
          ? const Value.absent()
          : Value(noveltySummary),
      newEntityIds: newEntityIds == null && nullToAbsent
          ? const Value.absent()
          : Value(newEntityIds),
      playerStrategy: playerStrategy == null && nullToAbsent
          ? const Value.absent()
          : Value(playerStrategy),
      strategyTags: strategyTags == null && nullToAbsent
          ? const Value.absent()
          : Value(strategyTags),
    );
  }

  factory TurnRow.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return TurnRow(
      id: serializer.fromJson<int>(json['id']),
      civId: serializer.fromJson<int>(json['civId']),
      turnNumber: serializer.fromJson<int>(json['turnNumber']),
      title: serializer.fromJson<String?>(json['title']),
      summary: serializer.fromJson<String?>(json['summary']),
      detailedSummary: serializer.fromJson<String?>(json['detailedSummary']),
      rawMessageIds: serializer.fromJson<String>(json['rawMessageIds']),
      turnType: serializer.fromJson<String>(json['turnType']),
      gameDateStart: serializer.fromJson<String?>(json['gameDateStart']),
      gameDateEnd: serializer.fromJson<String?>(json['gameDateEnd']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
      processedAt: serializer.fromJson<String?>(json['processedAt']),
      thematicTags: serializer.fromJson<String?>(json['thematicTags']),
      technologies: serializer.fromJson<String?>(json['technologies']),
      resources: serializer.fromJson<String?>(json['resources']),
      beliefs: serializer.fromJson<String?>(json['beliefs']),
      geography: serializer.fromJson<String?>(json['geography']),
      keyEvents: serializer.fromJson<String?>(json['keyEvents']),
      choicesMade: serializer.fromJson<String?>(json['choicesMade']),
      choicesProposed: serializer.fromJson<String?>(json['choicesProposed']),
      techEra: serializer.fromJson<String?>(json['techEra']),
      fantasyLevel: serializer.fromJson<String?>(json['fantasyLevel']),
      noveltySummary: serializer.fromJson<String?>(json['noveltySummary']),
      newEntityIds: serializer.fromJson<String?>(json['newEntityIds']),
      playerStrategy: serializer.fromJson<String?>(json['playerStrategy']),
      strategyTags: serializer.fromJson<String?>(json['strategyTags']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'civId': serializer.toJson<int>(civId),
      'turnNumber': serializer.toJson<int>(turnNumber),
      'title': serializer.toJson<String?>(title),
      'summary': serializer.toJson<String?>(summary),
      'detailedSummary': serializer.toJson<String?>(detailedSummary),
      'rawMessageIds': serializer.toJson<String>(rawMessageIds),
      'turnType': serializer.toJson<String>(turnType),
      'gameDateStart': serializer.toJson<String?>(gameDateStart),
      'gameDateEnd': serializer.toJson<String?>(gameDateEnd),
      'createdAt': serializer.toJson<String>(createdAt),
      'processedAt': serializer.toJson<String?>(processedAt),
      'thematicTags': serializer.toJson<String?>(thematicTags),
      'technologies': serializer.toJson<String?>(technologies),
      'resources': serializer.toJson<String?>(resources),
      'beliefs': serializer.toJson<String?>(beliefs),
      'geography': serializer.toJson<String?>(geography),
      'keyEvents': serializer.toJson<String?>(keyEvents),
      'choicesMade': serializer.toJson<String?>(choicesMade),
      'choicesProposed': serializer.toJson<String?>(choicesProposed),
      'techEra': serializer.toJson<String?>(techEra),
      'fantasyLevel': serializer.toJson<String?>(fantasyLevel),
      'noveltySummary': serializer.toJson<String?>(noveltySummary),
      'newEntityIds': serializer.toJson<String?>(newEntityIds),
      'playerStrategy': serializer.toJson<String?>(playerStrategy),
      'strategyTags': serializer.toJson<String?>(strategyTags),
    };
  }

  TurnRow copyWith(
          {int? id,
          int? civId,
          int? turnNumber,
          Value<String?> title = const Value.absent(),
          Value<String?> summary = const Value.absent(),
          Value<String?> detailedSummary = const Value.absent(),
          String? rawMessageIds,
          String? turnType,
          Value<String?> gameDateStart = const Value.absent(),
          Value<String?> gameDateEnd = const Value.absent(),
          String? createdAt,
          Value<String?> processedAt = const Value.absent(),
          Value<String?> thematicTags = const Value.absent(),
          Value<String?> technologies = const Value.absent(),
          Value<String?> resources = const Value.absent(),
          Value<String?> beliefs = const Value.absent(),
          Value<String?> geography = const Value.absent(),
          Value<String?> keyEvents = const Value.absent(),
          Value<String?> choicesMade = const Value.absent(),
          Value<String?> choicesProposed = const Value.absent(),
          Value<String?> techEra = const Value.absent(),
          Value<String?> fantasyLevel = const Value.absent(),
          Value<String?> noveltySummary = const Value.absent(),
          Value<String?> newEntityIds = const Value.absent(),
          Value<String?> playerStrategy = const Value.absent(),
          Value<String?> strategyTags = const Value.absent()}) =>
      TurnRow(
        id: id ?? this.id,
        civId: civId ?? this.civId,
        turnNumber: turnNumber ?? this.turnNumber,
        title: title.present ? title.value : this.title,
        summary: summary.present ? summary.value : this.summary,
        detailedSummary: detailedSummary.present
            ? detailedSummary.value
            : this.detailedSummary,
        rawMessageIds: rawMessageIds ?? this.rawMessageIds,
        turnType: turnType ?? this.turnType,
        gameDateStart:
            gameDateStart.present ? gameDateStart.value : this.gameDateStart,
        gameDateEnd: gameDateEnd.present ? gameDateEnd.value : this.gameDateEnd,
        createdAt: createdAt ?? this.createdAt,
        processedAt: processedAt.present ? processedAt.value : this.processedAt,
        thematicTags:
            thematicTags.present ? thematicTags.value : this.thematicTags,
        technologies:
            technologies.present ? technologies.value : this.technologies,
        resources: resources.present ? resources.value : this.resources,
        beliefs: beliefs.present ? beliefs.value : this.beliefs,
        geography: geography.present ? geography.value : this.geography,
        keyEvents: keyEvents.present ? keyEvents.value : this.keyEvents,
        choicesMade: choicesMade.present ? choicesMade.value : this.choicesMade,
        choicesProposed: choicesProposed.present
            ? choicesProposed.value
            : this.choicesProposed,
        techEra: techEra.present ? techEra.value : this.techEra,
        fantasyLevel:
            fantasyLevel.present ? fantasyLevel.value : this.fantasyLevel,
        noveltySummary:
            noveltySummary.present ? noveltySummary.value : this.noveltySummary,
        newEntityIds:
            newEntityIds.present ? newEntityIds.value : this.newEntityIds,
        playerStrategy:
            playerStrategy.present ? playerStrategy.value : this.playerStrategy,
        strategyTags:
            strategyTags.present ? strategyTags.value : this.strategyTags,
      );
  TurnRow copyWithCompanion(TurnTurnsCompanion data) {
    return TurnRow(
      id: data.id.present ? data.id.value : this.id,
      civId: data.civId.present ? data.civId.value : this.civId,
      turnNumber:
          data.turnNumber.present ? data.turnNumber.value : this.turnNumber,
      title: data.title.present ? data.title.value : this.title,
      summary: data.summary.present ? data.summary.value : this.summary,
      detailedSummary: data.detailedSummary.present
          ? data.detailedSummary.value
          : this.detailedSummary,
      rawMessageIds: data.rawMessageIds.present
          ? data.rawMessageIds.value
          : this.rawMessageIds,
      turnType: data.turnType.present ? data.turnType.value : this.turnType,
      gameDateStart: data.gameDateStart.present
          ? data.gameDateStart.value
          : this.gameDateStart,
      gameDateEnd:
          data.gameDateEnd.present ? data.gameDateEnd.value : this.gameDateEnd,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      processedAt:
          data.processedAt.present ? data.processedAt.value : this.processedAt,
      thematicTags: data.thematicTags.present
          ? data.thematicTags.value
          : this.thematicTags,
      technologies: data.technologies.present
          ? data.technologies.value
          : this.technologies,
      resources: data.resources.present ? data.resources.value : this.resources,
      beliefs: data.beliefs.present ? data.beliefs.value : this.beliefs,
      geography: data.geography.present ? data.geography.value : this.geography,
      keyEvents: data.keyEvents.present ? data.keyEvents.value : this.keyEvents,
      choicesMade:
          data.choicesMade.present ? data.choicesMade.value : this.choicesMade,
      choicesProposed: data.choicesProposed.present
          ? data.choicesProposed.value
          : this.choicesProposed,
      techEra: data.techEra.present ? data.techEra.value : this.techEra,
      fantasyLevel: data.fantasyLevel.present
          ? data.fantasyLevel.value
          : this.fantasyLevel,
      noveltySummary: data.noveltySummary.present
          ? data.noveltySummary.value
          : this.noveltySummary,
      newEntityIds: data.newEntityIds.present
          ? data.newEntityIds.value
          : this.newEntityIds,
      playerStrategy: data.playerStrategy.present
          ? data.playerStrategy.value
          : this.playerStrategy,
      strategyTags: data.strategyTags.present
          ? data.strategyTags.value
          : this.strategyTags,
    );
  }

  @override
  String toString() {
    return (StringBuffer('TurnRow(')
          ..write('id: $id, ')
          ..write('civId: $civId, ')
          ..write('turnNumber: $turnNumber, ')
          ..write('title: $title, ')
          ..write('summary: $summary, ')
          ..write('detailedSummary: $detailedSummary, ')
          ..write('rawMessageIds: $rawMessageIds, ')
          ..write('turnType: $turnType, ')
          ..write('gameDateStart: $gameDateStart, ')
          ..write('gameDateEnd: $gameDateEnd, ')
          ..write('createdAt: $createdAt, ')
          ..write('processedAt: $processedAt, ')
          ..write('thematicTags: $thematicTags, ')
          ..write('technologies: $technologies, ')
          ..write('resources: $resources, ')
          ..write('beliefs: $beliefs, ')
          ..write('geography: $geography, ')
          ..write('keyEvents: $keyEvents, ')
          ..write('choicesMade: $choicesMade, ')
          ..write('choicesProposed: $choicesProposed, ')
          ..write('techEra: $techEra, ')
          ..write('fantasyLevel: $fantasyLevel, ')
          ..write('noveltySummary: $noveltySummary, ')
          ..write('newEntityIds: $newEntityIds, ')
          ..write('playerStrategy: $playerStrategy, ')
          ..write('strategyTags: $strategyTags')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hashAll([
        id,
        civId,
        turnNumber,
        title,
        summary,
        detailedSummary,
        rawMessageIds,
        turnType,
        gameDateStart,
        gameDateEnd,
        createdAt,
        processedAt,
        thematicTags,
        technologies,
        resources,
        beliefs,
        geography,
        keyEvents,
        choicesMade,
        choicesProposed,
        techEra,
        fantasyLevel,
        noveltySummary,
        newEntityIds,
        playerStrategy,
        strategyTags
      ]);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is TurnRow &&
          other.id == this.id &&
          other.civId == this.civId &&
          other.turnNumber == this.turnNumber &&
          other.title == this.title &&
          other.summary == this.summary &&
          other.detailedSummary == this.detailedSummary &&
          other.rawMessageIds == this.rawMessageIds &&
          other.turnType == this.turnType &&
          other.gameDateStart == this.gameDateStart &&
          other.gameDateEnd == this.gameDateEnd &&
          other.createdAt == this.createdAt &&
          other.processedAt == this.processedAt &&
          other.thematicTags == this.thematicTags &&
          other.technologies == this.technologies &&
          other.resources == this.resources &&
          other.beliefs == this.beliefs &&
          other.geography == this.geography &&
          other.keyEvents == this.keyEvents &&
          other.choicesMade == this.choicesMade &&
          other.choicesProposed == this.choicesProposed &&
          other.techEra == this.techEra &&
          other.fantasyLevel == this.fantasyLevel &&
          other.noveltySummary == this.noveltySummary &&
          other.newEntityIds == this.newEntityIds &&
          other.playerStrategy == this.playerStrategy &&
          other.strategyTags == this.strategyTags);
}

class TurnTurnsCompanion extends UpdateCompanion<TurnRow> {
  final Value<int> id;
  final Value<int> civId;
  final Value<int> turnNumber;
  final Value<String?> title;
  final Value<String?> summary;
  final Value<String?> detailedSummary;
  final Value<String> rawMessageIds;
  final Value<String> turnType;
  final Value<String?> gameDateStart;
  final Value<String?> gameDateEnd;
  final Value<String> createdAt;
  final Value<String?> processedAt;
  final Value<String?> thematicTags;
  final Value<String?> technologies;
  final Value<String?> resources;
  final Value<String?> beliefs;
  final Value<String?> geography;
  final Value<String?> keyEvents;
  final Value<String?> choicesMade;
  final Value<String?> choicesProposed;
  final Value<String?> techEra;
  final Value<String?> fantasyLevel;
  final Value<String?> noveltySummary;
  final Value<String?> newEntityIds;
  final Value<String?> playerStrategy;
  final Value<String?> strategyTags;
  const TurnTurnsCompanion({
    this.id = const Value.absent(),
    this.civId = const Value.absent(),
    this.turnNumber = const Value.absent(),
    this.title = const Value.absent(),
    this.summary = const Value.absent(),
    this.detailedSummary = const Value.absent(),
    this.rawMessageIds = const Value.absent(),
    this.turnType = const Value.absent(),
    this.gameDateStart = const Value.absent(),
    this.gameDateEnd = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.processedAt = const Value.absent(),
    this.thematicTags = const Value.absent(),
    this.technologies = const Value.absent(),
    this.resources = const Value.absent(),
    this.beliefs = const Value.absent(),
    this.geography = const Value.absent(),
    this.keyEvents = const Value.absent(),
    this.choicesMade = const Value.absent(),
    this.choicesProposed = const Value.absent(),
    this.techEra = const Value.absent(),
    this.fantasyLevel = const Value.absent(),
    this.noveltySummary = const Value.absent(),
    this.newEntityIds = const Value.absent(),
    this.playerStrategy = const Value.absent(),
    this.strategyTags = const Value.absent(),
  });
  TurnTurnsCompanion.insert({
    this.id = const Value.absent(),
    required int civId,
    required int turnNumber,
    this.title = const Value.absent(),
    this.summary = const Value.absent(),
    this.detailedSummary = const Value.absent(),
    required String rawMessageIds,
    this.turnType = const Value.absent(),
    this.gameDateStart = const Value.absent(),
    this.gameDateEnd = const Value.absent(),
    required String createdAt,
    this.processedAt = const Value.absent(),
    this.thematicTags = const Value.absent(),
    this.technologies = const Value.absent(),
    this.resources = const Value.absent(),
    this.beliefs = const Value.absent(),
    this.geography = const Value.absent(),
    this.keyEvents = const Value.absent(),
    this.choicesMade = const Value.absent(),
    this.choicesProposed = const Value.absent(),
    this.techEra = const Value.absent(),
    this.fantasyLevel = const Value.absent(),
    this.noveltySummary = const Value.absent(),
    this.newEntityIds = const Value.absent(),
    this.playerStrategy = const Value.absent(),
    this.strategyTags = const Value.absent(),
  })  : civId = Value(civId),
        turnNumber = Value(turnNumber),
        rawMessageIds = Value(rawMessageIds),
        createdAt = Value(createdAt);
  static Insertable<TurnRow> custom({
    Expression<int>? id,
    Expression<int>? civId,
    Expression<int>? turnNumber,
    Expression<String>? title,
    Expression<String>? summary,
    Expression<String>? detailedSummary,
    Expression<String>? rawMessageIds,
    Expression<String>? turnType,
    Expression<String>? gameDateStart,
    Expression<String>? gameDateEnd,
    Expression<String>? createdAt,
    Expression<String>? processedAt,
    Expression<String>? thematicTags,
    Expression<String>? technologies,
    Expression<String>? resources,
    Expression<String>? beliefs,
    Expression<String>? geography,
    Expression<String>? keyEvents,
    Expression<String>? choicesMade,
    Expression<String>? choicesProposed,
    Expression<String>? techEra,
    Expression<String>? fantasyLevel,
    Expression<String>? noveltySummary,
    Expression<String>? newEntityIds,
    Expression<String>? playerStrategy,
    Expression<String>? strategyTags,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (civId != null) 'civ_id': civId,
      if (turnNumber != null) 'turn_number': turnNumber,
      if (title != null) 'title': title,
      if (summary != null) 'summary': summary,
      if (detailedSummary != null) 'detailed_summary': detailedSummary,
      if (rawMessageIds != null) 'raw_message_ids': rawMessageIds,
      if (turnType != null) 'turn_type': turnType,
      if (gameDateStart != null) 'game_date_start': gameDateStart,
      if (gameDateEnd != null) 'game_date_end': gameDateEnd,
      if (createdAt != null) 'created_at': createdAt,
      if (processedAt != null) 'processed_at': processedAt,
      if (thematicTags != null) 'thematic_tags': thematicTags,
      if (technologies != null) 'technologies': technologies,
      if (resources != null) 'resources': resources,
      if (beliefs != null) 'beliefs': beliefs,
      if (geography != null) 'geography': geography,
      if (keyEvents != null) 'key_events': keyEvents,
      if (choicesMade != null) 'choices_made': choicesMade,
      if (choicesProposed != null) 'choices_proposed': choicesProposed,
      if (techEra != null) 'tech_era': techEra,
      if (fantasyLevel != null) 'fantasy_level': fantasyLevel,
      if (noveltySummary != null) 'novelty_summary': noveltySummary,
      if (newEntityIds != null) 'new_entity_ids': newEntityIds,
      if (playerStrategy != null) 'player_strategy': playerStrategy,
      if (strategyTags != null) 'strategy_tags': strategyTags,
    });
  }

  TurnTurnsCompanion copyWith(
      {Value<int>? id,
      Value<int>? civId,
      Value<int>? turnNumber,
      Value<String?>? title,
      Value<String?>? summary,
      Value<String?>? detailedSummary,
      Value<String>? rawMessageIds,
      Value<String>? turnType,
      Value<String?>? gameDateStart,
      Value<String?>? gameDateEnd,
      Value<String>? createdAt,
      Value<String?>? processedAt,
      Value<String?>? thematicTags,
      Value<String?>? technologies,
      Value<String?>? resources,
      Value<String?>? beliefs,
      Value<String?>? geography,
      Value<String?>? keyEvents,
      Value<String?>? choicesMade,
      Value<String?>? choicesProposed,
      Value<String?>? techEra,
      Value<String?>? fantasyLevel,
      Value<String?>? noveltySummary,
      Value<String?>? newEntityIds,
      Value<String?>? playerStrategy,
      Value<String?>? strategyTags}) {
    return TurnTurnsCompanion(
      id: id ?? this.id,
      civId: civId ?? this.civId,
      turnNumber: turnNumber ?? this.turnNumber,
      title: title ?? this.title,
      summary: summary ?? this.summary,
      detailedSummary: detailedSummary ?? this.detailedSummary,
      rawMessageIds: rawMessageIds ?? this.rawMessageIds,
      turnType: turnType ?? this.turnType,
      gameDateStart: gameDateStart ?? this.gameDateStart,
      gameDateEnd: gameDateEnd ?? this.gameDateEnd,
      createdAt: createdAt ?? this.createdAt,
      processedAt: processedAt ?? this.processedAt,
      thematicTags: thematicTags ?? this.thematicTags,
      technologies: technologies ?? this.technologies,
      resources: resources ?? this.resources,
      beliefs: beliefs ?? this.beliefs,
      geography: geography ?? this.geography,
      keyEvents: keyEvents ?? this.keyEvents,
      choicesMade: choicesMade ?? this.choicesMade,
      choicesProposed: choicesProposed ?? this.choicesProposed,
      techEra: techEra ?? this.techEra,
      fantasyLevel: fantasyLevel ?? this.fantasyLevel,
      noveltySummary: noveltySummary ?? this.noveltySummary,
      newEntityIds: newEntityIds ?? this.newEntityIds,
      playerStrategy: playerStrategy ?? this.playerStrategy,
      strategyTags: strategyTags ?? this.strategyTags,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (civId.present) {
      map['civ_id'] = Variable<int>(civId.value);
    }
    if (turnNumber.present) {
      map['turn_number'] = Variable<int>(turnNumber.value);
    }
    if (title.present) {
      map['title'] = Variable<String>(title.value);
    }
    if (summary.present) {
      map['summary'] = Variable<String>(summary.value);
    }
    if (detailedSummary.present) {
      map['detailed_summary'] = Variable<String>(detailedSummary.value);
    }
    if (rawMessageIds.present) {
      map['raw_message_ids'] = Variable<String>(rawMessageIds.value);
    }
    if (turnType.present) {
      map['turn_type'] = Variable<String>(turnType.value);
    }
    if (gameDateStart.present) {
      map['game_date_start'] = Variable<String>(gameDateStart.value);
    }
    if (gameDateEnd.present) {
      map['game_date_end'] = Variable<String>(gameDateEnd.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    if (processedAt.present) {
      map['processed_at'] = Variable<String>(processedAt.value);
    }
    if (thematicTags.present) {
      map['thematic_tags'] = Variable<String>(thematicTags.value);
    }
    if (technologies.present) {
      map['technologies'] = Variable<String>(technologies.value);
    }
    if (resources.present) {
      map['resources'] = Variable<String>(resources.value);
    }
    if (beliefs.present) {
      map['beliefs'] = Variable<String>(beliefs.value);
    }
    if (geography.present) {
      map['geography'] = Variable<String>(geography.value);
    }
    if (keyEvents.present) {
      map['key_events'] = Variable<String>(keyEvents.value);
    }
    if (choicesMade.present) {
      map['choices_made'] = Variable<String>(choicesMade.value);
    }
    if (choicesProposed.present) {
      map['choices_proposed'] = Variable<String>(choicesProposed.value);
    }
    if (techEra.present) {
      map['tech_era'] = Variable<String>(techEra.value);
    }
    if (fantasyLevel.present) {
      map['fantasy_level'] = Variable<String>(fantasyLevel.value);
    }
    if (noveltySummary.present) {
      map['novelty_summary'] = Variable<String>(noveltySummary.value);
    }
    if (newEntityIds.present) {
      map['new_entity_ids'] = Variable<String>(newEntityIds.value);
    }
    if (playerStrategy.present) {
      map['player_strategy'] = Variable<String>(playerStrategy.value);
    }
    if (strategyTags.present) {
      map['strategy_tags'] = Variable<String>(strategyTags.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('TurnTurnsCompanion(')
          ..write('id: $id, ')
          ..write('civId: $civId, ')
          ..write('turnNumber: $turnNumber, ')
          ..write('title: $title, ')
          ..write('summary: $summary, ')
          ..write('detailedSummary: $detailedSummary, ')
          ..write('rawMessageIds: $rawMessageIds, ')
          ..write('turnType: $turnType, ')
          ..write('gameDateStart: $gameDateStart, ')
          ..write('gameDateEnd: $gameDateEnd, ')
          ..write('createdAt: $createdAt, ')
          ..write('processedAt: $processedAt, ')
          ..write('thematicTags: $thematicTags, ')
          ..write('technologies: $technologies, ')
          ..write('resources: $resources, ')
          ..write('beliefs: $beliefs, ')
          ..write('geography: $geography, ')
          ..write('keyEvents: $keyEvents, ')
          ..write('choicesMade: $choicesMade, ')
          ..write('choicesProposed: $choicesProposed, ')
          ..write('techEra: $techEra, ')
          ..write('fantasyLevel: $fantasyLevel, ')
          ..write('noveltySummary: $noveltySummary, ')
          ..write('newEntityIds: $newEntityIds, ')
          ..write('playerStrategy: $playerStrategy, ')
          ..write('strategyTags: $strategyTags')
          ..write(')'))
        .toString();
  }
}

class $TurnSegmentsTable extends TurnSegments
    with TableInfo<$TurnSegmentsTable, SegmentRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $TurnSegmentsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
      'id', aliasedName, false,
      hasAutoIncrement: true,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('PRIMARY KEY AUTOINCREMENT'));
  static const VerificationMeta _turnIdMeta = const VerificationMeta('turnId');
  @override
  late final GeneratedColumn<int> turnId = GeneratedColumn<int>(
      'turn_id', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _segmentOrderMeta =
      const VerificationMeta('segmentOrder');
  @override
  late final GeneratedColumn<int> segmentOrder = GeneratedColumn<int>(
      'segment_order', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _segmentTypeMeta =
      const VerificationMeta('segmentType');
  @override
  late final GeneratedColumn<String> segmentType = GeneratedColumn<String>(
      'segment_type', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _contentMeta =
      const VerificationMeta('content');
  @override
  late final GeneratedColumn<String> content = GeneratedColumn<String>(
      'content', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _sourceMeta = const VerificationMeta('source');
  @override
  late final GeneratedColumn<String> source = GeneratedColumn<String>(
      'source', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('gm'));
  @override
  List<GeneratedColumn> get $columns =>
      [id, turnId, segmentOrder, segmentType, content, source];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'turn_segments';
  @override
  VerificationContext validateIntegrity(Insertable<SegmentRow> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('turn_id')) {
      context.handle(_turnIdMeta,
          turnId.isAcceptableOrUnknown(data['turn_id']!, _turnIdMeta));
    } else if (isInserting) {
      context.missing(_turnIdMeta);
    }
    if (data.containsKey('segment_order')) {
      context.handle(
          _segmentOrderMeta,
          segmentOrder.isAcceptableOrUnknown(
              data['segment_order']!, _segmentOrderMeta));
    } else if (isInserting) {
      context.missing(_segmentOrderMeta);
    }
    if (data.containsKey('segment_type')) {
      context.handle(
          _segmentTypeMeta,
          segmentType.isAcceptableOrUnknown(
              data['segment_type']!, _segmentTypeMeta));
    } else if (isInserting) {
      context.missing(_segmentTypeMeta);
    }
    if (data.containsKey('content')) {
      context.handle(_contentMeta,
          content.isAcceptableOrUnknown(data['content']!, _contentMeta));
    } else if (isInserting) {
      context.missing(_contentMeta);
    }
    if (data.containsKey('source')) {
      context.handle(_sourceMeta,
          source.isAcceptableOrUnknown(data['source']!, _sourceMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  SegmentRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return SegmentRow(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}id'])!,
      turnId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}turn_id'])!,
      segmentOrder: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}segment_order'])!,
      segmentType: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}segment_type'])!,
      content: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}content'])!,
      source: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}source'])!,
    );
  }

  @override
  $TurnSegmentsTable createAlias(String alias) {
    return $TurnSegmentsTable(attachedDatabase, alias);
  }
}

class SegmentRow extends DataClass implements Insertable<SegmentRow> {
  final int id;
  final int turnId;
  final int segmentOrder;
  final String segmentType;
  final String content;
  final String source;
  const SegmentRow(
      {required this.id,
      required this.turnId,
      required this.segmentOrder,
      required this.segmentType,
      required this.content,
      required this.source});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['turn_id'] = Variable<int>(turnId);
    map['segment_order'] = Variable<int>(segmentOrder);
    map['segment_type'] = Variable<String>(segmentType);
    map['content'] = Variable<String>(content);
    map['source'] = Variable<String>(source);
    return map;
  }

  TurnSegmentsCompanion toCompanion(bool nullToAbsent) {
    return TurnSegmentsCompanion(
      id: Value(id),
      turnId: Value(turnId),
      segmentOrder: Value(segmentOrder),
      segmentType: Value(segmentType),
      content: Value(content),
      source: Value(source),
    );
  }

  factory SegmentRow.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return SegmentRow(
      id: serializer.fromJson<int>(json['id']),
      turnId: serializer.fromJson<int>(json['turnId']),
      segmentOrder: serializer.fromJson<int>(json['segmentOrder']),
      segmentType: serializer.fromJson<String>(json['segmentType']),
      content: serializer.fromJson<String>(json['content']),
      source: serializer.fromJson<String>(json['source']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'turnId': serializer.toJson<int>(turnId),
      'segmentOrder': serializer.toJson<int>(segmentOrder),
      'segmentType': serializer.toJson<String>(segmentType),
      'content': serializer.toJson<String>(content),
      'source': serializer.toJson<String>(source),
    };
  }

  SegmentRow copyWith(
          {int? id,
          int? turnId,
          int? segmentOrder,
          String? segmentType,
          String? content,
          String? source}) =>
      SegmentRow(
        id: id ?? this.id,
        turnId: turnId ?? this.turnId,
        segmentOrder: segmentOrder ?? this.segmentOrder,
        segmentType: segmentType ?? this.segmentType,
        content: content ?? this.content,
        source: source ?? this.source,
      );
  SegmentRow copyWithCompanion(TurnSegmentsCompanion data) {
    return SegmentRow(
      id: data.id.present ? data.id.value : this.id,
      turnId: data.turnId.present ? data.turnId.value : this.turnId,
      segmentOrder: data.segmentOrder.present
          ? data.segmentOrder.value
          : this.segmentOrder,
      segmentType:
          data.segmentType.present ? data.segmentType.value : this.segmentType,
      content: data.content.present ? data.content.value : this.content,
      source: data.source.present ? data.source.value : this.source,
    );
  }

  @override
  String toString() {
    return (StringBuffer('SegmentRow(')
          ..write('id: $id, ')
          ..write('turnId: $turnId, ')
          ..write('segmentOrder: $segmentOrder, ')
          ..write('segmentType: $segmentType, ')
          ..write('content: $content, ')
          ..write('source: $source')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode =>
      Object.hash(id, turnId, segmentOrder, segmentType, content, source);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is SegmentRow &&
          other.id == this.id &&
          other.turnId == this.turnId &&
          other.segmentOrder == this.segmentOrder &&
          other.segmentType == this.segmentType &&
          other.content == this.content &&
          other.source == this.source);
}

class TurnSegmentsCompanion extends UpdateCompanion<SegmentRow> {
  final Value<int> id;
  final Value<int> turnId;
  final Value<int> segmentOrder;
  final Value<String> segmentType;
  final Value<String> content;
  final Value<String> source;
  const TurnSegmentsCompanion({
    this.id = const Value.absent(),
    this.turnId = const Value.absent(),
    this.segmentOrder = const Value.absent(),
    this.segmentType = const Value.absent(),
    this.content = const Value.absent(),
    this.source = const Value.absent(),
  });
  TurnSegmentsCompanion.insert({
    this.id = const Value.absent(),
    required int turnId,
    required int segmentOrder,
    required String segmentType,
    required String content,
    this.source = const Value.absent(),
  })  : turnId = Value(turnId),
        segmentOrder = Value(segmentOrder),
        segmentType = Value(segmentType),
        content = Value(content);
  static Insertable<SegmentRow> custom({
    Expression<int>? id,
    Expression<int>? turnId,
    Expression<int>? segmentOrder,
    Expression<String>? segmentType,
    Expression<String>? content,
    Expression<String>? source,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (turnId != null) 'turn_id': turnId,
      if (segmentOrder != null) 'segment_order': segmentOrder,
      if (segmentType != null) 'segment_type': segmentType,
      if (content != null) 'content': content,
      if (source != null) 'source': source,
    });
  }

  TurnSegmentsCompanion copyWith(
      {Value<int>? id,
      Value<int>? turnId,
      Value<int>? segmentOrder,
      Value<String>? segmentType,
      Value<String>? content,
      Value<String>? source}) {
    return TurnSegmentsCompanion(
      id: id ?? this.id,
      turnId: turnId ?? this.turnId,
      segmentOrder: segmentOrder ?? this.segmentOrder,
      segmentType: segmentType ?? this.segmentType,
      content: content ?? this.content,
      source: source ?? this.source,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (turnId.present) {
      map['turn_id'] = Variable<int>(turnId.value);
    }
    if (segmentOrder.present) {
      map['segment_order'] = Variable<int>(segmentOrder.value);
    }
    if (segmentType.present) {
      map['segment_type'] = Variable<String>(segmentType.value);
    }
    if (content.present) {
      map['content'] = Variable<String>(content.value);
    }
    if (source.present) {
      map['source'] = Variable<String>(source.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('TurnSegmentsCompanion(')
          ..write('id: $id, ')
          ..write('turnId: $turnId, ')
          ..write('segmentOrder: $segmentOrder, ')
          ..write('segmentType: $segmentType, ')
          ..write('content: $content, ')
          ..write('source: $source')
          ..write(')'))
        .toString();
  }
}

class $EntityEntitiesTable extends EntityEntities
    with TableInfo<$EntityEntitiesTable, EntityRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $EntityEntitiesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
      'id', aliasedName, false,
      hasAutoIncrement: true,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('PRIMARY KEY AUTOINCREMENT'));
  static const VerificationMeta _canonicalNameMeta =
      const VerificationMeta('canonicalName');
  @override
  late final GeneratedColumn<String> canonicalName = GeneratedColumn<String>(
      'canonical_name', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _entityTypeMeta =
      const VerificationMeta('entityType');
  @override
  late final GeneratedColumn<String> entityType = GeneratedColumn<String>(
      'entity_type', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _civIdMeta = const VerificationMeta('civId');
  @override
  late final GeneratedColumn<int> civId = GeneratedColumn<int>(
      'civ_id', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _descriptionMeta =
      const VerificationMeta('description');
  @override
  late final GeneratedColumn<String> description = GeneratedColumn<String>(
      'description', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _firstSeenTurnMeta =
      const VerificationMeta('firstSeenTurn');
  @override
  late final GeneratedColumn<int> firstSeenTurn = GeneratedColumn<int>(
      'first_seen_turn', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _lastSeenTurnMeta =
      const VerificationMeta('lastSeenTurn');
  @override
  late final GeneratedColumn<int> lastSeenTurn = GeneratedColumn<int>(
      'last_seen_turn', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _isActiveMeta =
      const VerificationMeta('isActive');
  @override
  late final GeneratedColumn<int> isActive = GeneratedColumn<int>(
      'is_active', aliasedName, false,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultValue: const Constant(1));
  static const VerificationMeta _createdAtMeta =
      const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
      'created_at', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _updatedAtMeta =
      const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<String> updatedAt = GeneratedColumn<String>(
      'updated_at', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _hiddenMeta = const VerificationMeta('hidden');
  @override
  late final GeneratedColumn<bool> hidden = GeneratedColumn<bool>(
      'hidden', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("hidden" IN (0, 1))'),
      defaultValue: const Constant(false));
  static const VerificationMeta _disabledMeta =
      const VerificationMeta('disabled');
  @override
  late final GeneratedColumn<bool> disabled = GeneratedColumn<bool>(
      'disabled', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("disabled" IN (0, 1))'),
      defaultValue: const Constant(false));
  static const VerificationMeta _disabledAtMeta =
      const VerificationMeta('disabledAt');
  @override
  late final GeneratedColumn<String> disabledAt = GeneratedColumn<String>(
      'disabled_at', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _tagsMeta = const VerificationMeta('tags');
  @override
  late final GeneratedColumn<String> tags = GeneratedColumn<String>(
      'tags', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  @override
  List<GeneratedColumn> get $columns => [
        id,
        canonicalName,
        entityType,
        civId,
        description,
        firstSeenTurn,
        lastSeenTurn,
        isActive,
        createdAt,
        updatedAt,
        hidden,
        disabled,
        disabledAt,
        tags
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'entity_entities';
  @override
  VerificationContext validateIntegrity(Insertable<EntityRow> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('canonical_name')) {
      context.handle(
          _canonicalNameMeta,
          canonicalName.isAcceptableOrUnknown(
              data['canonical_name']!, _canonicalNameMeta));
    } else if (isInserting) {
      context.missing(_canonicalNameMeta);
    }
    if (data.containsKey('entity_type')) {
      context.handle(
          _entityTypeMeta,
          entityType.isAcceptableOrUnknown(
              data['entity_type']!, _entityTypeMeta));
    } else if (isInserting) {
      context.missing(_entityTypeMeta);
    }
    if (data.containsKey('civ_id')) {
      context.handle(
          _civIdMeta, civId.isAcceptableOrUnknown(data['civ_id']!, _civIdMeta));
    }
    if (data.containsKey('description')) {
      context.handle(
          _descriptionMeta,
          description.isAcceptableOrUnknown(
              data['description']!, _descriptionMeta));
    }
    if (data.containsKey('first_seen_turn')) {
      context.handle(
          _firstSeenTurnMeta,
          firstSeenTurn.isAcceptableOrUnknown(
              data['first_seen_turn']!, _firstSeenTurnMeta));
    }
    if (data.containsKey('last_seen_turn')) {
      context.handle(
          _lastSeenTurnMeta,
          lastSeenTurn.isAcceptableOrUnknown(
              data['last_seen_turn']!, _lastSeenTurnMeta));
    }
    if (data.containsKey('is_active')) {
      context.handle(_isActiveMeta,
          isActive.isAcceptableOrUnknown(data['is_active']!, _isActiveMeta));
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta,
          createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta,
          updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    if (data.containsKey('hidden')) {
      context.handle(_hiddenMeta,
          hidden.isAcceptableOrUnknown(data['hidden']!, _hiddenMeta));
    }
    if (data.containsKey('disabled')) {
      context.handle(_disabledMeta,
          disabled.isAcceptableOrUnknown(data['disabled']!, _disabledMeta));
    }
    if (data.containsKey('disabled_at')) {
      context.handle(
          _disabledAtMeta,
          disabledAt.isAcceptableOrUnknown(
              data['disabled_at']!, _disabledAtMeta));
    }
    if (data.containsKey('tags')) {
      context.handle(
          _tagsMeta, tags.isAcceptableOrUnknown(data['tags']!, _tagsMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  EntityRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return EntityRow(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}id'])!,
      canonicalName: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}canonical_name'])!,
      entityType: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}entity_type'])!,
      civId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}civ_id']),
      description: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}description']),
      firstSeenTurn: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}first_seen_turn']),
      lastSeenTurn: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}last_seen_turn']),
      isActive: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}is_active'])!,
      createdAt: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}created_at'])!,
      updatedAt: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}updated_at'])!,
      hidden: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}hidden'])!,
      disabled: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}disabled'])!,
      disabledAt: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}disabled_at']),
      tags: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}tags']),
    );
  }

  @override
  $EntityEntitiesTable createAlias(String alias) {
    return $EntityEntitiesTable(attachedDatabase, alias);
  }
}

class EntityRow extends DataClass implements Insertable<EntityRow> {
  final int id;
  final String canonicalName;
  final String entityType;
  final int? civId;
  final String? description;
  final int? firstSeenTurn;
  final int? lastSeenTurn;
  final int isActive;
  final String createdAt;
  final String updatedAt;
  final bool hidden;
  final bool disabled;
  final String? disabledAt;
  final String? tags;
  const EntityRow(
      {required this.id,
      required this.canonicalName,
      required this.entityType,
      this.civId,
      this.description,
      this.firstSeenTurn,
      this.lastSeenTurn,
      required this.isActive,
      required this.createdAt,
      required this.updatedAt,
      required this.hidden,
      required this.disabled,
      this.disabledAt,
      this.tags});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['canonical_name'] = Variable<String>(canonicalName);
    map['entity_type'] = Variable<String>(entityType);
    if (!nullToAbsent || civId != null) {
      map['civ_id'] = Variable<int>(civId);
    }
    if (!nullToAbsent || description != null) {
      map['description'] = Variable<String>(description);
    }
    if (!nullToAbsent || firstSeenTurn != null) {
      map['first_seen_turn'] = Variable<int>(firstSeenTurn);
    }
    if (!nullToAbsent || lastSeenTurn != null) {
      map['last_seen_turn'] = Variable<int>(lastSeenTurn);
    }
    map['is_active'] = Variable<int>(isActive);
    map['created_at'] = Variable<String>(createdAt);
    map['updated_at'] = Variable<String>(updatedAt);
    map['hidden'] = Variable<bool>(hidden);
    map['disabled'] = Variable<bool>(disabled);
    if (!nullToAbsent || disabledAt != null) {
      map['disabled_at'] = Variable<String>(disabledAt);
    }
    if (!nullToAbsent || tags != null) {
      map['tags'] = Variable<String>(tags);
    }
    return map;
  }

  EntityEntitiesCompanion toCompanion(bool nullToAbsent) {
    return EntityEntitiesCompanion(
      id: Value(id),
      canonicalName: Value(canonicalName),
      entityType: Value(entityType),
      civId:
          civId == null && nullToAbsent ? const Value.absent() : Value(civId),
      description: description == null && nullToAbsent
          ? const Value.absent()
          : Value(description),
      firstSeenTurn: firstSeenTurn == null && nullToAbsent
          ? const Value.absent()
          : Value(firstSeenTurn),
      lastSeenTurn: lastSeenTurn == null && nullToAbsent
          ? const Value.absent()
          : Value(lastSeenTurn),
      isActive: Value(isActive),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      hidden: Value(hidden),
      disabled: Value(disabled),
      disabledAt: disabledAt == null && nullToAbsent
          ? const Value.absent()
          : Value(disabledAt),
      tags: tags == null && nullToAbsent ? const Value.absent() : Value(tags),
    );
  }

  factory EntityRow.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return EntityRow(
      id: serializer.fromJson<int>(json['id']),
      canonicalName: serializer.fromJson<String>(json['canonicalName']),
      entityType: serializer.fromJson<String>(json['entityType']),
      civId: serializer.fromJson<int?>(json['civId']),
      description: serializer.fromJson<String?>(json['description']),
      firstSeenTurn: serializer.fromJson<int?>(json['firstSeenTurn']),
      lastSeenTurn: serializer.fromJson<int?>(json['lastSeenTurn']),
      isActive: serializer.fromJson<int>(json['isActive']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
      updatedAt: serializer.fromJson<String>(json['updatedAt']),
      hidden: serializer.fromJson<bool>(json['hidden']),
      disabled: serializer.fromJson<bool>(json['disabled']),
      disabledAt: serializer.fromJson<String?>(json['disabledAt']),
      tags: serializer.fromJson<String?>(json['tags']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'canonicalName': serializer.toJson<String>(canonicalName),
      'entityType': serializer.toJson<String>(entityType),
      'civId': serializer.toJson<int?>(civId),
      'description': serializer.toJson<String?>(description),
      'firstSeenTurn': serializer.toJson<int?>(firstSeenTurn),
      'lastSeenTurn': serializer.toJson<int?>(lastSeenTurn),
      'isActive': serializer.toJson<int>(isActive),
      'createdAt': serializer.toJson<String>(createdAt),
      'updatedAt': serializer.toJson<String>(updatedAt),
      'hidden': serializer.toJson<bool>(hidden),
      'disabled': serializer.toJson<bool>(disabled),
      'disabledAt': serializer.toJson<String?>(disabledAt),
      'tags': serializer.toJson<String?>(tags),
    };
  }

  EntityRow copyWith(
          {int? id,
          String? canonicalName,
          String? entityType,
          Value<int?> civId = const Value.absent(),
          Value<String?> description = const Value.absent(),
          Value<int?> firstSeenTurn = const Value.absent(),
          Value<int?> lastSeenTurn = const Value.absent(),
          int? isActive,
          String? createdAt,
          String? updatedAt,
          bool? hidden,
          bool? disabled,
          Value<String?> disabledAt = const Value.absent(),
          Value<String?> tags = const Value.absent()}) =>
      EntityRow(
        id: id ?? this.id,
        canonicalName: canonicalName ?? this.canonicalName,
        entityType: entityType ?? this.entityType,
        civId: civId.present ? civId.value : this.civId,
        description: description.present ? description.value : this.description,
        firstSeenTurn:
            firstSeenTurn.present ? firstSeenTurn.value : this.firstSeenTurn,
        lastSeenTurn:
            lastSeenTurn.present ? lastSeenTurn.value : this.lastSeenTurn,
        isActive: isActive ?? this.isActive,
        createdAt: createdAt ?? this.createdAt,
        updatedAt: updatedAt ?? this.updatedAt,
        hidden: hidden ?? this.hidden,
        disabled: disabled ?? this.disabled,
        disabledAt: disabledAt.present ? disabledAt.value : this.disabledAt,
        tags: tags.present ? tags.value : this.tags,
      );
  EntityRow copyWithCompanion(EntityEntitiesCompanion data) {
    return EntityRow(
      id: data.id.present ? data.id.value : this.id,
      canonicalName: data.canonicalName.present
          ? data.canonicalName.value
          : this.canonicalName,
      entityType:
          data.entityType.present ? data.entityType.value : this.entityType,
      civId: data.civId.present ? data.civId.value : this.civId,
      description:
          data.description.present ? data.description.value : this.description,
      firstSeenTurn: data.firstSeenTurn.present
          ? data.firstSeenTurn.value
          : this.firstSeenTurn,
      lastSeenTurn: data.lastSeenTurn.present
          ? data.lastSeenTurn.value
          : this.lastSeenTurn,
      isActive: data.isActive.present ? data.isActive.value : this.isActive,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      hidden: data.hidden.present ? data.hidden.value : this.hidden,
      disabled: data.disabled.present ? data.disabled.value : this.disabled,
      disabledAt:
          data.disabledAt.present ? data.disabledAt.value : this.disabledAt,
      tags: data.tags.present ? data.tags.value : this.tags,
    );
  }

  @override
  String toString() {
    return (StringBuffer('EntityRow(')
          ..write('id: $id, ')
          ..write('canonicalName: $canonicalName, ')
          ..write('entityType: $entityType, ')
          ..write('civId: $civId, ')
          ..write('description: $description, ')
          ..write('firstSeenTurn: $firstSeenTurn, ')
          ..write('lastSeenTurn: $lastSeenTurn, ')
          ..write('isActive: $isActive, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('hidden: $hidden, ')
          ..write('disabled: $disabled, ')
          ..write('disabledAt: $disabledAt, ')
          ..write('tags: $tags')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
      id,
      canonicalName,
      entityType,
      civId,
      description,
      firstSeenTurn,
      lastSeenTurn,
      isActive,
      createdAt,
      updatedAt,
      hidden,
      disabled,
      disabledAt,
      tags);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is EntityRow &&
          other.id == this.id &&
          other.canonicalName == this.canonicalName &&
          other.entityType == this.entityType &&
          other.civId == this.civId &&
          other.description == this.description &&
          other.firstSeenTurn == this.firstSeenTurn &&
          other.lastSeenTurn == this.lastSeenTurn &&
          other.isActive == this.isActive &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.hidden == this.hidden &&
          other.disabled == this.disabled &&
          other.disabledAt == this.disabledAt &&
          other.tags == this.tags);
}

class EntityEntitiesCompanion extends UpdateCompanion<EntityRow> {
  final Value<int> id;
  final Value<String> canonicalName;
  final Value<String> entityType;
  final Value<int?> civId;
  final Value<String?> description;
  final Value<int?> firstSeenTurn;
  final Value<int?> lastSeenTurn;
  final Value<int> isActive;
  final Value<String> createdAt;
  final Value<String> updatedAt;
  final Value<bool> hidden;
  final Value<bool> disabled;
  final Value<String?> disabledAt;
  final Value<String?> tags;
  const EntityEntitiesCompanion({
    this.id = const Value.absent(),
    this.canonicalName = const Value.absent(),
    this.entityType = const Value.absent(),
    this.civId = const Value.absent(),
    this.description = const Value.absent(),
    this.firstSeenTurn = const Value.absent(),
    this.lastSeenTurn = const Value.absent(),
    this.isActive = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.hidden = const Value.absent(),
    this.disabled = const Value.absent(),
    this.disabledAt = const Value.absent(),
    this.tags = const Value.absent(),
  });
  EntityEntitiesCompanion.insert({
    this.id = const Value.absent(),
    required String canonicalName,
    required String entityType,
    this.civId = const Value.absent(),
    this.description = const Value.absent(),
    this.firstSeenTurn = const Value.absent(),
    this.lastSeenTurn = const Value.absent(),
    this.isActive = const Value.absent(),
    required String createdAt,
    required String updatedAt,
    this.hidden = const Value.absent(),
    this.disabled = const Value.absent(),
    this.disabledAt = const Value.absent(),
    this.tags = const Value.absent(),
  })  : canonicalName = Value(canonicalName),
        entityType = Value(entityType),
        createdAt = Value(createdAt),
        updatedAt = Value(updatedAt);
  static Insertable<EntityRow> custom({
    Expression<int>? id,
    Expression<String>? canonicalName,
    Expression<String>? entityType,
    Expression<int>? civId,
    Expression<String>? description,
    Expression<int>? firstSeenTurn,
    Expression<int>? lastSeenTurn,
    Expression<int>? isActive,
    Expression<String>? createdAt,
    Expression<String>? updatedAt,
    Expression<bool>? hidden,
    Expression<bool>? disabled,
    Expression<String>? disabledAt,
    Expression<String>? tags,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (canonicalName != null) 'canonical_name': canonicalName,
      if (entityType != null) 'entity_type': entityType,
      if (civId != null) 'civ_id': civId,
      if (description != null) 'description': description,
      if (firstSeenTurn != null) 'first_seen_turn': firstSeenTurn,
      if (lastSeenTurn != null) 'last_seen_turn': lastSeenTurn,
      if (isActive != null) 'is_active': isActive,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (hidden != null) 'hidden': hidden,
      if (disabled != null) 'disabled': disabled,
      if (disabledAt != null) 'disabled_at': disabledAt,
      if (tags != null) 'tags': tags,
    });
  }

  EntityEntitiesCompanion copyWith(
      {Value<int>? id,
      Value<String>? canonicalName,
      Value<String>? entityType,
      Value<int?>? civId,
      Value<String?>? description,
      Value<int?>? firstSeenTurn,
      Value<int?>? lastSeenTurn,
      Value<int>? isActive,
      Value<String>? createdAt,
      Value<String>? updatedAt,
      Value<bool>? hidden,
      Value<bool>? disabled,
      Value<String?>? disabledAt,
      Value<String?>? tags}) {
    return EntityEntitiesCompanion(
      id: id ?? this.id,
      canonicalName: canonicalName ?? this.canonicalName,
      entityType: entityType ?? this.entityType,
      civId: civId ?? this.civId,
      description: description ?? this.description,
      firstSeenTurn: firstSeenTurn ?? this.firstSeenTurn,
      lastSeenTurn: lastSeenTurn ?? this.lastSeenTurn,
      isActive: isActive ?? this.isActive,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      hidden: hidden ?? this.hidden,
      disabled: disabled ?? this.disabled,
      disabledAt: disabledAt ?? this.disabledAt,
      tags: tags ?? this.tags,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (canonicalName.present) {
      map['canonical_name'] = Variable<String>(canonicalName.value);
    }
    if (entityType.present) {
      map['entity_type'] = Variable<String>(entityType.value);
    }
    if (civId.present) {
      map['civ_id'] = Variable<int>(civId.value);
    }
    if (description.present) {
      map['description'] = Variable<String>(description.value);
    }
    if (firstSeenTurn.present) {
      map['first_seen_turn'] = Variable<int>(firstSeenTurn.value);
    }
    if (lastSeenTurn.present) {
      map['last_seen_turn'] = Variable<int>(lastSeenTurn.value);
    }
    if (isActive.present) {
      map['is_active'] = Variable<int>(isActive.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<String>(updatedAt.value);
    }
    if (hidden.present) {
      map['hidden'] = Variable<bool>(hidden.value);
    }
    if (disabled.present) {
      map['disabled'] = Variable<bool>(disabled.value);
    }
    if (disabledAt.present) {
      map['disabled_at'] = Variable<String>(disabledAt.value);
    }
    if (tags.present) {
      map['tags'] = Variable<String>(tags.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('EntityEntitiesCompanion(')
          ..write('id: $id, ')
          ..write('canonicalName: $canonicalName, ')
          ..write('entityType: $entityType, ')
          ..write('civId: $civId, ')
          ..write('description: $description, ')
          ..write('firstSeenTurn: $firstSeenTurn, ')
          ..write('lastSeenTurn: $lastSeenTurn, ')
          ..write('isActive: $isActive, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('hidden: $hidden, ')
          ..write('disabled: $disabled, ')
          ..write('disabledAt: $disabledAt, ')
          ..write('tags: $tags')
          ..write(')'))
        .toString();
  }
}

class $EntityAliasesTable extends EntityAliases
    with TableInfo<$EntityAliasesTable, AliasRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $EntityAliasesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
      'id', aliasedName, false,
      hasAutoIncrement: true,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('PRIMARY KEY AUTOINCREMENT'));
  static const VerificationMeta _entityIdMeta =
      const VerificationMeta('entityId');
  @override
  late final GeneratedColumn<int> entityId = GeneratedColumn<int>(
      'entity_id', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _aliasMeta = const VerificationMeta('alias');
  @override
  late final GeneratedColumn<String> alias = GeneratedColumn<String>(
      'alias', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _firstSeenTurnIdMeta =
      const VerificationMeta('firstSeenTurnId');
  @override
  late final GeneratedColumn<int> firstSeenTurnId = GeneratedColumn<int>(
      'first_seen_turn_id', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  @override
  List<GeneratedColumn> get $columns => [id, entityId, alias, firstSeenTurnId];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'entity_aliases';
  @override
  VerificationContext validateIntegrity(Insertable<AliasRow> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('entity_id')) {
      context.handle(_entityIdMeta,
          entityId.isAcceptableOrUnknown(data['entity_id']!, _entityIdMeta));
    } else if (isInserting) {
      context.missing(_entityIdMeta);
    }
    if (data.containsKey('alias')) {
      context.handle(
          _aliasMeta, alias.isAcceptableOrUnknown(data['alias']!, _aliasMeta));
    } else if (isInserting) {
      context.missing(_aliasMeta);
    }
    if (data.containsKey('first_seen_turn_id')) {
      context.handle(
          _firstSeenTurnIdMeta,
          firstSeenTurnId.isAcceptableOrUnknown(
              data['first_seen_turn_id']!, _firstSeenTurnIdMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  AliasRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return AliasRow(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}id'])!,
      entityId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}entity_id'])!,
      alias: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}alias'])!,
      firstSeenTurnId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}first_seen_turn_id']),
    );
  }

  @override
  $EntityAliasesTable createAlias(String alias) {
    return $EntityAliasesTable(attachedDatabase, alias);
  }
}

class AliasRow extends DataClass implements Insertable<AliasRow> {
  final int id;
  final int entityId;
  final String alias;
  final int? firstSeenTurnId;
  const AliasRow(
      {required this.id,
      required this.entityId,
      required this.alias,
      this.firstSeenTurnId});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['entity_id'] = Variable<int>(entityId);
    map['alias'] = Variable<String>(alias);
    if (!nullToAbsent || firstSeenTurnId != null) {
      map['first_seen_turn_id'] = Variable<int>(firstSeenTurnId);
    }
    return map;
  }

  EntityAliasesCompanion toCompanion(bool nullToAbsent) {
    return EntityAliasesCompanion(
      id: Value(id),
      entityId: Value(entityId),
      alias: Value(alias),
      firstSeenTurnId: firstSeenTurnId == null && nullToAbsent
          ? const Value.absent()
          : Value(firstSeenTurnId),
    );
  }

  factory AliasRow.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return AliasRow(
      id: serializer.fromJson<int>(json['id']),
      entityId: serializer.fromJson<int>(json['entityId']),
      alias: serializer.fromJson<String>(json['alias']),
      firstSeenTurnId: serializer.fromJson<int?>(json['firstSeenTurnId']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'entityId': serializer.toJson<int>(entityId),
      'alias': serializer.toJson<String>(alias),
      'firstSeenTurnId': serializer.toJson<int?>(firstSeenTurnId),
    };
  }

  AliasRow copyWith(
          {int? id,
          int? entityId,
          String? alias,
          Value<int?> firstSeenTurnId = const Value.absent()}) =>
      AliasRow(
        id: id ?? this.id,
        entityId: entityId ?? this.entityId,
        alias: alias ?? this.alias,
        firstSeenTurnId: firstSeenTurnId.present
            ? firstSeenTurnId.value
            : this.firstSeenTurnId,
      );
  AliasRow copyWithCompanion(EntityAliasesCompanion data) {
    return AliasRow(
      id: data.id.present ? data.id.value : this.id,
      entityId: data.entityId.present ? data.entityId.value : this.entityId,
      alias: data.alias.present ? data.alias.value : this.alias,
      firstSeenTurnId: data.firstSeenTurnId.present
          ? data.firstSeenTurnId.value
          : this.firstSeenTurnId,
    );
  }

  @override
  String toString() {
    return (StringBuffer('AliasRow(')
          ..write('id: $id, ')
          ..write('entityId: $entityId, ')
          ..write('alias: $alias, ')
          ..write('firstSeenTurnId: $firstSeenTurnId')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, entityId, alias, firstSeenTurnId);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is AliasRow &&
          other.id == this.id &&
          other.entityId == this.entityId &&
          other.alias == this.alias &&
          other.firstSeenTurnId == this.firstSeenTurnId);
}

class EntityAliasesCompanion extends UpdateCompanion<AliasRow> {
  final Value<int> id;
  final Value<int> entityId;
  final Value<String> alias;
  final Value<int?> firstSeenTurnId;
  const EntityAliasesCompanion({
    this.id = const Value.absent(),
    this.entityId = const Value.absent(),
    this.alias = const Value.absent(),
    this.firstSeenTurnId = const Value.absent(),
  });
  EntityAliasesCompanion.insert({
    this.id = const Value.absent(),
    required int entityId,
    required String alias,
    this.firstSeenTurnId = const Value.absent(),
  })  : entityId = Value(entityId),
        alias = Value(alias);
  static Insertable<AliasRow> custom({
    Expression<int>? id,
    Expression<int>? entityId,
    Expression<String>? alias,
    Expression<int>? firstSeenTurnId,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (entityId != null) 'entity_id': entityId,
      if (alias != null) 'alias': alias,
      if (firstSeenTurnId != null) 'first_seen_turn_id': firstSeenTurnId,
    });
  }

  EntityAliasesCompanion copyWith(
      {Value<int>? id,
      Value<int>? entityId,
      Value<String>? alias,
      Value<int?>? firstSeenTurnId}) {
    return EntityAliasesCompanion(
      id: id ?? this.id,
      entityId: entityId ?? this.entityId,
      alias: alias ?? this.alias,
      firstSeenTurnId: firstSeenTurnId ?? this.firstSeenTurnId,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (entityId.present) {
      map['entity_id'] = Variable<int>(entityId.value);
    }
    if (alias.present) {
      map['alias'] = Variable<String>(alias.value);
    }
    if (firstSeenTurnId.present) {
      map['first_seen_turn_id'] = Variable<int>(firstSeenTurnId.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('EntityAliasesCompanion(')
          ..write('id: $id, ')
          ..write('entityId: $entityId, ')
          ..write('alias: $alias, ')
          ..write('firstSeenTurnId: $firstSeenTurnId')
          ..write(')'))
        .toString();
  }
}

class $EntityMentionsTable extends EntityMentions
    with TableInfo<$EntityMentionsTable, MentionRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $EntityMentionsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
      'id', aliasedName, false,
      hasAutoIncrement: true,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('PRIMARY KEY AUTOINCREMENT'));
  static const VerificationMeta _entityIdMeta =
      const VerificationMeta('entityId');
  @override
  late final GeneratedColumn<int> entityId = GeneratedColumn<int>(
      'entity_id', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _turnIdMeta = const VerificationMeta('turnId');
  @override
  late final GeneratedColumn<int> turnId = GeneratedColumn<int>(
      'turn_id', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _segmentIdMeta =
      const VerificationMeta('segmentId');
  @override
  late final GeneratedColumn<int> segmentId = GeneratedColumn<int>(
      'segment_id', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _mentionTextMeta =
      const VerificationMeta('mentionText');
  @override
  late final GeneratedColumn<String> mentionText = GeneratedColumn<String>(
      'mention_text', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _contextMeta =
      const VerificationMeta('context');
  @override
  late final GeneratedColumn<String> context = GeneratedColumn<String>(
      'context', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _sourceMeta = const VerificationMeta('source');
  @override
  late final GeneratedColumn<String> source = GeneratedColumn<String>(
      'source', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('gm'));
  @override
  List<GeneratedColumn> get $columns =>
      [id, entityId, turnId, segmentId, mentionText, context, source];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'entity_mentions';
  @override
  VerificationContext validateIntegrity(Insertable<MentionRow> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('entity_id')) {
      context.handle(_entityIdMeta,
          entityId.isAcceptableOrUnknown(data['entity_id']!, _entityIdMeta));
    } else if (isInserting) {
      context.missing(_entityIdMeta);
    }
    if (data.containsKey('turn_id')) {
      context.handle(_turnIdMeta,
          turnId.isAcceptableOrUnknown(data['turn_id']!, _turnIdMeta));
    } else if (isInserting) {
      context.missing(_turnIdMeta);
    }
    if (data.containsKey('segment_id')) {
      context.handle(_segmentIdMeta,
          segmentId.isAcceptableOrUnknown(data['segment_id']!, _segmentIdMeta));
    }
    if (data.containsKey('mention_text')) {
      context.handle(
          _mentionTextMeta,
          mentionText.isAcceptableOrUnknown(
              data['mention_text']!, _mentionTextMeta));
    } else if (isInserting) {
      context.missing(_mentionTextMeta);
    }
    if (data.containsKey('context')) {
      context.handle(_contextMeta,
          this.context.isAcceptableOrUnknown(data['context']!, _contextMeta));
    }
    if (data.containsKey('source')) {
      context.handle(_sourceMeta,
          source.isAcceptableOrUnknown(data['source']!, _sourceMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  MentionRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return MentionRow(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}id'])!,
      entityId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}entity_id'])!,
      turnId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}turn_id'])!,
      segmentId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}segment_id']),
      mentionText: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}mention_text'])!,
      context: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}context']),
      source: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}source'])!,
    );
  }

  @override
  $EntityMentionsTable createAlias(String alias) {
    return $EntityMentionsTable(attachedDatabase, alias);
  }
}

class MentionRow extends DataClass implements Insertable<MentionRow> {
  final int id;
  final int entityId;
  final int turnId;
  final int? segmentId;
  final String mentionText;
  final String? context;
  final String source;
  const MentionRow(
      {required this.id,
      required this.entityId,
      required this.turnId,
      this.segmentId,
      required this.mentionText,
      this.context,
      required this.source});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['entity_id'] = Variable<int>(entityId);
    map['turn_id'] = Variable<int>(turnId);
    if (!nullToAbsent || segmentId != null) {
      map['segment_id'] = Variable<int>(segmentId);
    }
    map['mention_text'] = Variable<String>(mentionText);
    if (!nullToAbsent || context != null) {
      map['context'] = Variable<String>(context);
    }
    map['source'] = Variable<String>(source);
    return map;
  }

  EntityMentionsCompanion toCompanion(bool nullToAbsent) {
    return EntityMentionsCompanion(
      id: Value(id),
      entityId: Value(entityId),
      turnId: Value(turnId),
      segmentId: segmentId == null && nullToAbsent
          ? const Value.absent()
          : Value(segmentId),
      mentionText: Value(mentionText),
      context: context == null && nullToAbsent
          ? const Value.absent()
          : Value(context),
      source: Value(source),
    );
  }

  factory MentionRow.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return MentionRow(
      id: serializer.fromJson<int>(json['id']),
      entityId: serializer.fromJson<int>(json['entityId']),
      turnId: serializer.fromJson<int>(json['turnId']),
      segmentId: serializer.fromJson<int?>(json['segmentId']),
      mentionText: serializer.fromJson<String>(json['mentionText']),
      context: serializer.fromJson<String?>(json['context']),
      source: serializer.fromJson<String>(json['source']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'entityId': serializer.toJson<int>(entityId),
      'turnId': serializer.toJson<int>(turnId),
      'segmentId': serializer.toJson<int?>(segmentId),
      'mentionText': serializer.toJson<String>(mentionText),
      'context': serializer.toJson<String?>(context),
      'source': serializer.toJson<String>(source),
    };
  }

  MentionRow copyWith(
          {int? id,
          int? entityId,
          int? turnId,
          Value<int?> segmentId = const Value.absent(),
          String? mentionText,
          Value<String?> context = const Value.absent(),
          String? source}) =>
      MentionRow(
        id: id ?? this.id,
        entityId: entityId ?? this.entityId,
        turnId: turnId ?? this.turnId,
        segmentId: segmentId.present ? segmentId.value : this.segmentId,
        mentionText: mentionText ?? this.mentionText,
        context: context.present ? context.value : this.context,
        source: source ?? this.source,
      );
  MentionRow copyWithCompanion(EntityMentionsCompanion data) {
    return MentionRow(
      id: data.id.present ? data.id.value : this.id,
      entityId: data.entityId.present ? data.entityId.value : this.entityId,
      turnId: data.turnId.present ? data.turnId.value : this.turnId,
      segmentId: data.segmentId.present ? data.segmentId.value : this.segmentId,
      mentionText:
          data.mentionText.present ? data.mentionText.value : this.mentionText,
      context: data.context.present ? data.context.value : this.context,
      source: data.source.present ? data.source.value : this.source,
    );
  }

  @override
  String toString() {
    return (StringBuffer('MentionRow(')
          ..write('id: $id, ')
          ..write('entityId: $entityId, ')
          ..write('turnId: $turnId, ')
          ..write('segmentId: $segmentId, ')
          ..write('mentionText: $mentionText, ')
          ..write('context: $context, ')
          ..write('source: $source')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
      id, entityId, turnId, segmentId, mentionText, context, source);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is MentionRow &&
          other.id == this.id &&
          other.entityId == this.entityId &&
          other.turnId == this.turnId &&
          other.segmentId == this.segmentId &&
          other.mentionText == this.mentionText &&
          other.context == this.context &&
          other.source == this.source);
}

class EntityMentionsCompanion extends UpdateCompanion<MentionRow> {
  final Value<int> id;
  final Value<int> entityId;
  final Value<int> turnId;
  final Value<int?> segmentId;
  final Value<String> mentionText;
  final Value<String?> context;
  final Value<String> source;
  const EntityMentionsCompanion({
    this.id = const Value.absent(),
    this.entityId = const Value.absent(),
    this.turnId = const Value.absent(),
    this.segmentId = const Value.absent(),
    this.mentionText = const Value.absent(),
    this.context = const Value.absent(),
    this.source = const Value.absent(),
  });
  EntityMentionsCompanion.insert({
    this.id = const Value.absent(),
    required int entityId,
    required int turnId,
    this.segmentId = const Value.absent(),
    required String mentionText,
    this.context = const Value.absent(),
    this.source = const Value.absent(),
  })  : entityId = Value(entityId),
        turnId = Value(turnId),
        mentionText = Value(mentionText);
  static Insertable<MentionRow> custom({
    Expression<int>? id,
    Expression<int>? entityId,
    Expression<int>? turnId,
    Expression<int>? segmentId,
    Expression<String>? mentionText,
    Expression<String>? context,
    Expression<String>? source,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (entityId != null) 'entity_id': entityId,
      if (turnId != null) 'turn_id': turnId,
      if (segmentId != null) 'segment_id': segmentId,
      if (mentionText != null) 'mention_text': mentionText,
      if (context != null) 'context': context,
      if (source != null) 'source': source,
    });
  }

  EntityMentionsCompanion copyWith(
      {Value<int>? id,
      Value<int>? entityId,
      Value<int>? turnId,
      Value<int?>? segmentId,
      Value<String>? mentionText,
      Value<String?>? context,
      Value<String>? source}) {
    return EntityMentionsCompanion(
      id: id ?? this.id,
      entityId: entityId ?? this.entityId,
      turnId: turnId ?? this.turnId,
      segmentId: segmentId ?? this.segmentId,
      mentionText: mentionText ?? this.mentionText,
      context: context ?? this.context,
      source: source ?? this.source,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (entityId.present) {
      map['entity_id'] = Variable<int>(entityId.value);
    }
    if (turnId.present) {
      map['turn_id'] = Variable<int>(turnId.value);
    }
    if (segmentId.present) {
      map['segment_id'] = Variable<int>(segmentId.value);
    }
    if (mentionText.present) {
      map['mention_text'] = Variable<String>(mentionText.value);
    }
    if (context.present) {
      map['context'] = Variable<String>(context.value);
    }
    if (source.present) {
      map['source'] = Variable<String>(source.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('EntityMentionsCompanion(')
          ..write('id: $id, ')
          ..write('entityId: $entityId, ')
          ..write('turnId: $turnId, ')
          ..write('segmentId: $segmentId, ')
          ..write('mentionText: $mentionText, ')
          ..write('context: $context, ')
          ..write('source: $source')
          ..write(')'))
        .toString();
  }
}

class $EntityRelationsTable extends EntityRelations
    with TableInfo<$EntityRelationsTable, RelationRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $EntityRelationsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
      'id', aliasedName, false,
      hasAutoIncrement: true,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('PRIMARY KEY AUTOINCREMENT'));
  static const VerificationMeta _sourceEntityIdMeta =
      const VerificationMeta('sourceEntityId');
  @override
  late final GeneratedColumn<int> sourceEntityId = GeneratedColumn<int>(
      'source_entity_id', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _targetEntityIdMeta =
      const VerificationMeta('targetEntityId');
  @override
  late final GeneratedColumn<int> targetEntityId = GeneratedColumn<int>(
      'target_entity_id', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _relationTypeMeta =
      const VerificationMeta('relationType');
  @override
  late final GeneratedColumn<String> relationType = GeneratedColumn<String>(
      'relation_type', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _descriptionMeta =
      const VerificationMeta('description');
  @override
  late final GeneratedColumn<String> description = GeneratedColumn<String>(
      'description', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _turnIdMeta = const VerificationMeta('turnId');
  @override
  late final GeneratedColumn<int> turnId = GeneratedColumn<int>(
      'turn_id', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _isActiveMeta =
      const VerificationMeta('isActive');
  @override
  late final GeneratedColumn<int> isActive = GeneratedColumn<int>(
      'is_active', aliasedName, false,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultValue: const Constant(1));
  static const VerificationMeta _createdAtMeta =
      const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
      'created_at', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  @override
  List<GeneratedColumn> get $columns => [
        id,
        sourceEntityId,
        targetEntityId,
        relationType,
        description,
        turnId,
        isActive,
        createdAt
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'entity_relations';
  @override
  VerificationContext validateIntegrity(Insertable<RelationRow> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('source_entity_id')) {
      context.handle(
          _sourceEntityIdMeta,
          sourceEntityId.isAcceptableOrUnknown(
              data['source_entity_id']!, _sourceEntityIdMeta));
    } else if (isInserting) {
      context.missing(_sourceEntityIdMeta);
    }
    if (data.containsKey('target_entity_id')) {
      context.handle(
          _targetEntityIdMeta,
          targetEntityId.isAcceptableOrUnknown(
              data['target_entity_id']!, _targetEntityIdMeta));
    } else if (isInserting) {
      context.missing(_targetEntityIdMeta);
    }
    if (data.containsKey('relation_type')) {
      context.handle(
          _relationTypeMeta,
          relationType.isAcceptableOrUnknown(
              data['relation_type']!, _relationTypeMeta));
    } else if (isInserting) {
      context.missing(_relationTypeMeta);
    }
    if (data.containsKey('description')) {
      context.handle(
          _descriptionMeta,
          description.isAcceptableOrUnknown(
              data['description']!, _descriptionMeta));
    }
    if (data.containsKey('turn_id')) {
      context.handle(_turnIdMeta,
          turnId.isAcceptableOrUnknown(data['turn_id']!, _turnIdMeta));
    }
    if (data.containsKey('is_active')) {
      context.handle(_isActiveMeta,
          isActive.isAcceptableOrUnknown(data['is_active']!, _isActiveMeta));
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta,
          createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  RelationRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return RelationRow(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}id'])!,
      sourceEntityId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}source_entity_id'])!,
      targetEntityId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}target_entity_id'])!,
      relationType: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}relation_type'])!,
      description: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}description']),
      turnId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}turn_id']),
      isActive: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}is_active'])!,
      createdAt: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}created_at'])!,
    );
  }

  @override
  $EntityRelationsTable createAlias(String alias) {
    return $EntityRelationsTable(attachedDatabase, alias);
  }
}

class RelationRow extends DataClass implements Insertable<RelationRow> {
  final int id;
  final int sourceEntityId;
  final int targetEntityId;
  final String relationType;
  final String? description;
  final int? turnId;
  final int isActive;
  final String createdAt;
  const RelationRow(
      {required this.id,
      required this.sourceEntityId,
      required this.targetEntityId,
      required this.relationType,
      this.description,
      this.turnId,
      required this.isActive,
      required this.createdAt});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['source_entity_id'] = Variable<int>(sourceEntityId);
    map['target_entity_id'] = Variable<int>(targetEntityId);
    map['relation_type'] = Variable<String>(relationType);
    if (!nullToAbsent || description != null) {
      map['description'] = Variable<String>(description);
    }
    if (!nullToAbsent || turnId != null) {
      map['turn_id'] = Variable<int>(turnId);
    }
    map['is_active'] = Variable<int>(isActive);
    map['created_at'] = Variable<String>(createdAt);
    return map;
  }

  EntityRelationsCompanion toCompanion(bool nullToAbsent) {
    return EntityRelationsCompanion(
      id: Value(id),
      sourceEntityId: Value(sourceEntityId),
      targetEntityId: Value(targetEntityId),
      relationType: Value(relationType),
      description: description == null && nullToAbsent
          ? const Value.absent()
          : Value(description),
      turnId:
          turnId == null && nullToAbsent ? const Value.absent() : Value(turnId),
      isActive: Value(isActive),
      createdAt: Value(createdAt),
    );
  }

  factory RelationRow.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return RelationRow(
      id: serializer.fromJson<int>(json['id']),
      sourceEntityId: serializer.fromJson<int>(json['sourceEntityId']),
      targetEntityId: serializer.fromJson<int>(json['targetEntityId']),
      relationType: serializer.fromJson<String>(json['relationType']),
      description: serializer.fromJson<String?>(json['description']),
      turnId: serializer.fromJson<int?>(json['turnId']),
      isActive: serializer.fromJson<int>(json['isActive']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'sourceEntityId': serializer.toJson<int>(sourceEntityId),
      'targetEntityId': serializer.toJson<int>(targetEntityId),
      'relationType': serializer.toJson<String>(relationType),
      'description': serializer.toJson<String?>(description),
      'turnId': serializer.toJson<int?>(turnId),
      'isActive': serializer.toJson<int>(isActive),
      'createdAt': serializer.toJson<String>(createdAt),
    };
  }

  RelationRow copyWith(
          {int? id,
          int? sourceEntityId,
          int? targetEntityId,
          String? relationType,
          Value<String?> description = const Value.absent(),
          Value<int?> turnId = const Value.absent(),
          int? isActive,
          String? createdAt}) =>
      RelationRow(
        id: id ?? this.id,
        sourceEntityId: sourceEntityId ?? this.sourceEntityId,
        targetEntityId: targetEntityId ?? this.targetEntityId,
        relationType: relationType ?? this.relationType,
        description: description.present ? description.value : this.description,
        turnId: turnId.present ? turnId.value : this.turnId,
        isActive: isActive ?? this.isActive,
        createdAt: createdAt ?? this.createdAt,
      );
  RelationRow copyWithCompanion(EntityRelationsCompanion data) {
    return RelationRow(
      id: data.id.present ? data.id.value : this.id,
      sourceEntityId: data.sourceEntityId.present
          ? data.sourceEntityId.value
          : this.sourceEntityId,
      targetEntityId: data.targetEntityId.present
          ? data.targetEntityId.value
          : this.targetEntityId,
      relationType: data.relationType.present
          ? data.relationType.value
          : this.relationType,
      description:
          data.description.present ? data.description.value : this.description,
      turnId: data.turnId.present ? data.turnId.value : this.turnId,
      isActive: data.isActive.present ? data.isActive.value : this.isActive,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('RelationRow(')
          ..write('id: $id, ')
          ..write('sourceEntityId: $sourceEntityId, ')
          ..write('targetEntityId: $targetEntityId, ')
          ..write('relationType: $relationType, ')
          ..write('description: $description, ')
          ..write('turnId: $turnId, ')
          ..write('isActive: $isActive, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, sourceEntityId, targetEntityId,
      relationType, description, turnId, isActive, createdAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is RelationRow &&
          other.id == this.id &&
          other.sourceEntityId == this.sourceEntityId &&
          other.targetEntityId == this.targetEntityId &&
          other.relationType == this.relationType &&
          other.description == this.description &&
          other.turnId == this.turnId &&
          other.isActive == this.isActive &&
          other.createdAt == this.createdAt);
}

class EntityRelationsCompanion extends UpdateCompanion<RelationRow> {
  final Value<int> id;
  final Value<int> sourceEntityId;
  final Value<int> targetEntityId;
  final Value<String> relationType;
  final Value<String?> description;
  final Value<int?> turnId;
  final Value<int> isActive;
  final Value<String> createdAt;
  const EntityRelationsCompanion({
    this.id = const Value.absent(),
    this.sourceEntityId = const Value.absent(),
    this.targetEntityId = const Value.absent(),
    this.relationType = const Value.absent(),
    this.description = const Value.absent(),
    this.turnId = const Value.absent(),
    this.isActive = const Value.absent(),
    this.createdAt = const Value.absent(),
  });
  EntityRelationsCompanion.insert({
    this.id = const Value.absent(),
    required int sourceEntityId,
    required int targetEntityId,
    required String relationType,
    this.description = const Value.absent(),
    this.turnId = const Value.absent(),
    this.isActive = const Value.absent(),
    required String createdAt,
  })  : sourceEntityId = Value(sourceEntityId),
        targetEntityId = Value(targetEntityId),
        relationType = Value(relationType),
        createdAt = Value(createdAt);
  static Insertable<RelationRow> custom({
    Expression<int>? id,
    Expression<int>? sourceEntityId,
    Expression<int>? targetEntityId,
    Expression<String>? relationType,
    Expression<String>? description,
    Expression<int>? turnId,
    Expression<int>? isActive,
    Expression<String>? createdAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (sourceEntityId != null) 'source_entity_id': sourceEntityId,
      if (targetEntityId != null) 'target_entity_id': targetEntityId,
      if (relationType != null) 'relation_type': relationType,
      if (description != null) 'description': description,
      if (turnId != null) 'turn_id': turnId,
      if (isActive != null) 'is_active': isActive,
      if (createdAt != null) 'created_at': createdAt,
    });
  }

  EntityRelationsCompanion copyWith(
      {Value<int>? id,
      Value<int>? sourceEntityId,
      Value<int>? targetEntityId,
      Value<String>? relationType,
      Value<String?>? description,
      Value<int?>? turnId,
      Value<int>? isActive,
      Value<String>? createdAt}) {
    return EntityRelationsCompanion(
      id: id ?? this.id,
      sourceEntityId: sourceEntityId ?? this.sourceEntityId,
      targetEntityId: targetEntityId ?? this.targetEntityId,
      relationType: relationType ?? this.relationType,
      description: description ?? this.description,
      turnId: turnId ?? this.turnId,
      isActive: isActive ?? this.isActive,
      createdAt: createdAt ?? this.createdAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (sourceEntityId.present) {
      map['source_entity_id'] = Variable<int>(sourceEntityId.value);
    }
    if (targetEntityId.present) {
      map['target_entity_id'] = Variable<int>(targetEntityId.value);
    }
    if (relationType.present) {
      map['relation_type'] = Variable<String>(relationType.value);
    }
    if (description.present) {
      map['description'] = Variable<String>(description.value);
    }
    if (turnId.present) {
      map['turn_id'] = Variable<int>(turnId.value);
    }
    if (isActive.present) {
      map['is_active'] = Variable<int>(isActive.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('EntityRelationsCompanion(')
          ..write('id: $id, ')
          ..write('sourceEntityId: $sourceEntityId, ')
          ..write('targetEntityId: $targetEntityId, ')
          ..write('relationType: $relationType, ')
          ..write('description: $description, ')
          ..write('turnId: $turnId, ')
          ..write('isActive: $isActive, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }
}

class $PipelineRunsTable extends PipelineRuns
    with TableInfo<$PipelineRunsTable, PipelineRunRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $PipelineRunsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
      'id', aliasedName, false,
      hasAutoIncrement: true,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('PRIMARY KEY AUTOINCREMENT'));
  static const VerificationMeta _startedAtMeta =
      const VerificationMeta('startedAt');
  @override
  late final GeneratedColumn<String> startedAt = GeneratedColumn<String>(
      'started_at', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _completedAtMeta =
      const VerificationMeta('completedAt');
  @override
  late final GeneratedColumn<String> completedAt = GeneratedColumn<String>(
      'completed_at', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _statusMeta = const VerificationMeta('status');
  @override
  late final GeneratedColumn<String> status = GeneratedColumn<String>(
      'status', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('running'));
  static const VerificationMeta _messagesProcessedMeta =
      const VerificationMeta('messagesProcessed');
  @override
  late final GeneratedColumn<int> messagesProcessed = GeneratedColumn<int>(
      'messages_processed', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _turnsCreatedMeta =
      const VerificationMeta('turnsCreated');
  @override
  late final GeneratedColumn<int> turnsCreated = GeneratedColumn<int>(
      'turns_created', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _entitiesExtractedMeta =
      const VerificationMeta('entitiesExtracted');
  @override
  late final GeneratedColumn<int> entitiesExtracted = GeneratedColumn<int>(
      'entities_extracted', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _errorMessageMeta =
      const VerificationMeta('errorMessage');
  @override
  late final GeneratedColumn<String> errorMessage = GeneratedColumn<String>(
      'error_message', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  @override
  List<GeneratedColumn> get $columns => [
        id,
        startedAt,
        completedAt,
        status,
        messagesProcessed,
        turnsCreated,
        entitiesExtracted,
        errorMessage
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'pipeline_runs';
  @override
  VerificationContext validateIntegrity(Insertable<PipelineRunRow> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('started_at')) {
      context.handle(_startedAtMeta,
          startedAt.isAcceptableOrUnknown(data['started_at']!, _startedAtMeta));
    } else if (isInserting) {
      context.missing(_startedAtMeta);
    }
    if (data.containsKey('completed_at')) {
      context.handle(
          _completedAtMeta,
          completedAt.isAcceptableOrUnknown(
              data['completed_at']!, _completedAtMeta));
    }
    if (data.containsKey('status')) {
      context.handle(_statusMeta,
          status.isAcceptableOrUnknown(data['status']!, _statusMeta));
    }
    if (data.containsKey('messages_processed')) {
      context.handle(
          _messagesProcessedMeta,
          messagesProcessed.isAcceptableOrUnknown(
              data['messages_processed']!, _messagesProcessedMeta));
    }
    if (data.containsKey('turns_created')) {
      context.handle(
          _turnsCreatedMeta,
          turnsCreated.isAcceptableOrUnknown(
              data['turns_created']!, _turnsCreatedMeta));
    }
    if (data.containsKey('entities_extracted')) {
      context.handle(
          _entitiesExtractedMeta,
          entitiesExtracted.isAcceptableOrUnknown(
              data['entities_extracted']!, _entitiesExtractedMeta));
    }
    if (data.containsKey('error_message')) {
      context.handle(
          _errorMessageMeta,
          errorMessage.isAcceptableOrUnknown(
              data['error_message']!, _errorMessageMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  PipelineRunRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return PipelineRunRow(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}id'])!,
      startedAt: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}started_at'])!,
      completedAt: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}completed_at']),
      status: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}status'])!,
      messagesProcessed: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}messages_processed']),
      turnsCreated: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}turns_created']),
      entitiesExtracted: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}entities_extracted']),
      errorMessage: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}error_message']),
    );
  }

  @override
  $PipelineRunsTable createAlias(String alias) {
    return $PipelineRunsTable(attachedDatabase, alias);
  }
}

class PipelineRunRow extends DataClass implements Insertable<PipelineRunRow> {
  final int id;
  final String startedAt;
  final String? completedAt;
  final String status;
  final int? messagesProcessed;
  final int? turnsCreated;
  final int? entitiesExtracted;
  final String? errorMessage;
  const PipelineRunRow(
      {required this.id,
      required this.startedAt,
      this.completedAt,
      required this.status,
      this.messagesProcessed,
      this.turnsCreated,
      this.entitiesExtracted,
      this.errorMessage});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['started_at'] = Variable<String>(startedAt);
    if (!nullToAbsent || completedAt != null) {
      map['completed_at'] = Variable<String>(completedAt);
    }
    map['status'] = Variable<String>(status);
    if (!nullToAbsent || messagesProcessed != null) {
      map['messages_processed'] = Variable<int>(messagesProcessed);
    }
    if (!nullToAbsent || turnsCreated != null) {
      map['turns_created'] = Variable<int>(turnsCreated);
    }
    if (!nullToAbsent || entitiesExtracted != null) {
      map['entities_extracted'] = Variable<int>(entitiesExtracted);
    }
    if (!nullToAbsent || errorMessage != null) {
      map['error_message'] = Variable<String>(errorMessage);
    }
    return map;
  }

  PipelineRunsCompanion toCompanion(bool nullToAbsent) {
    return PipelineRunsCompanion(
      id: Value(id),
      startedAt: Value(startedAt),
      completedAt: completedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(completedAt),
      status: Value(status),
      messagesProcessed: messagesProcessed == null && nullToAbsent
          ? const Value.absent()
          : Value(messagesProcessed),
      turnsCreated: turnsCreated == null && nullToAbsent
          ? const Value.absent()
          : Value(turnsCreated),
      entitiesExtracted: entitiesExtracted == null && nullToAbsent
          ? const Value.absent()
          : Value(entitiesExtracted),
      errorMessage: errorMessage == null && nullToAbsent
          ? const Value.absent()
          : Value(errorMessage),
    );
  }

  factory PipelineRunRow.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return PipelineRunRow(
      id: serializer.fromJson<int>(json['id']),
      startedAt: serializer.fromJson<String>(json['startedAt']),
      completedAt: serializer.fromJson<String?>(json['completedAt']),
      status: serializer.fromJson<String>(json['status']),
      messagesProcessed: serializer.fromJson<int?>(json['messagesProcessed']),
      turnsCreated: serializer.fromJson<int?>(json['turnsCreated']),
      entitiesExtracted: serializer.fromJson<int?>(json['entitiesExtracted']),
      errorMessage: serializer.fromJson<String?>(json['errorMessage']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'startedAt': serializer.toJson<String>(startedAt),
      'completedAt': serializer.toJson<String?>(completedAt),
      'status': serializer.toJson<String>(status),
      'messagesProcessed': serializer.toJson<int?>(messagesProcessed),
      'turnsCreated': serializer.toJson<int?>(turnsCreated),
      'entitiesExtracted': serializer.toJson<int?>(entitiesExtracted),
      'errorMessage': serializer.toJson<String?>(errorMessage),
    };
  }

  PipelineRunRow copyWith(
          {int? id,
          String? startedAt,
          Value<String?> completedAt = const Value.absent(),
          String? status,
          Value<int?> messagesProcessed = const Value.absent(),
          Value<int?> turnsCreated = const Value.absent(),
          Value<int?> entitiesExtracted = const Value.absent(),
          Value<String?> errorMessage = const Value.absent()}) =>
      PipelineRunRow(
        id: id ?? this.id,
        startedAt: startedAt ?? this.startedAt,
        completedAt: completedAt.present ? completedAt.value : this.completedAt,
        status: status ?? this.status,
        messagesProcessed: messagesProcessed.present
            ? messagesProcessed.value
            : this.messagesProcessed,
        turnsCreated:
            turnsCreated.present ? turnsCreated.value : this.turnsCreated,
        entitiesExtracted: entitiesExtracted.present
            ? entitiesExtracted.value
            : this.entitiesExtracted,
        errorMessage:
            errorMessage.present ? errorMessage.value : this.errorMessage,
      );
  PipelineRunRow copyWithCompanion(PipelineRunsCompanion data) {
    return PipelineRunRow(
      id: data.id.present ? data.id.value : this.id,
      startedAt: data.startedAt.present ? data.startedAt.value : this.startedAt,
      completedAt:
          data.completedAt.present ? data.completedAt.value : this.completedAt,
      status: data.status.present ? data.status.value : this.status,
      messagesProcessed: data.messagesProcessed.present
          ? data.messagesProcessed.value
          : this.messagesProcessed,
      turnsCreated: data.turnsCreated.present
          ? data.turnsCreated.value
          : this.turnsCreated,
      entitiesExtracted: data.entitiesExtracted.present
          ? data.entitiesExtracted.value
          : this.entitiesExtracted,
      errorMessage: data.errorMessage.present
          ? data.errorMessage.value
          : this.errorMessage,
    );
  }

  @override
  String toString() {
    return (StringBuffer('PipelineRunRow(')
          ..write('id: $id, ')
          ..write('startedAt: $startedAt, ')
          ..write('completedAt: $completedAt, ')
          ..write('status: $status, ')
          ..write('messagesProcessed: $messagesProcessed, ')
          ..write('turnsCreated: $turnsCreated, ')
          ..write('entitiesExtracted: $entitiesExtracted, ')
          ..write('errorMessage: $errorMessage')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, startedAt, completedAt, status,
      messagesProcessed, turnsCreated, entitiesExtracted, errorMessage);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is PipelineRunRow &&
          other.id == this.id &&
          other.startedAt == this.startedAt &&
          other.completedAt == this.completedAt &&
          other.status == this.status &&
          other.messagesProcessed == this.messagesProcessed &&
          other.turnsCreated == this.turnsCreated &&
          other.entitiesExtracted == this.entitiesExtracted &&
          other.errorMessage == this.errorMessage);
}

class PipelineRunsCompanion extends UpdateCompanion<PipelineRunRow> {
  final Value<int> id;
  final Value<String> startedAt;
  final Value<String?> completedAt;
  final Value<String> status;
  final Value<int?> messagesProcessed;
  final Value<int?> turnsCreated;
  final Value<int?> entitiesExtracted;
  final Value<String?> errorMessage;
  const PipelineRunsCompanion({
    this.id = const Value.absent(),
    this.startedAt = const Value.absent(),
    this.completedAt = const Value.absent(),
    this.status = const Value.absent(),
    this.messagesProcessed = const Value.absent(),
    this.turnsCreated = const Value.absent(),
    this.entitiesExtracted = const Value.absent(),
    this.errorMessage = const Value.absent(),
  });
  PipelineRunsCompanion.insert({
    this.id = const Value.absent(),
    required String startedAt,
    this.completedAt = const Value.absent(),
    this.status = const Value.absent(),
    this.messagesProcessed = const Value.absent(),
    this.turnsCreated = const Value.absent(),
    this.entitiesExtracted = const Value.absent(),
    this.errorMessage = const Value.absent(),
  }) : startedAt = Value(startedAt);
  static Insertable<PipelineRunRow> custom({
    Expression<int>? id,
    Expression<String>? startedAt,
    Expression<String>? completedAt,
    Expression<String>? status,
    Expression<int>? messagesProcessed,
    Expression<int>? turnsCreated,
    Expression<int>? entitiesExtracted,
    Expression<String>? errorMessage,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (startedAt != null) 'started_at': startedAt,
      if (completedAt != null) 'completed_at': completedAt,
      if (status != null) 'status': status,
      if (messagesProcessed != null) 'messages_processed': messagesProcessed,
      if (turnsCreated != null) 'turns_created': turnsCreated,
      if (entitiesExtracted != null) 'entities_extracted': entitiesExtracted,
      if (errorMessage != null) 'error_message': errorMessage,
    });
  }

  PipelineRunsCompanion copyWith(
      {Value<int>? id,
      Value<String>? startedAt,
      Value<String?>? completedAt,
      Value<String>? status,
      Value<int?>? messagesProcessed,
      Value<int?>? turnsCreated,
      Value<int?>? entitiesExtracted,
      Value<String?>? errorMessage}) {
    return PipelineRunsCompanion(
      id: id ?? this.id,
      startedAt: startedAt ?? this.startedAt,
      completedAt: completedAt ?? this.completedAt,
      status: status ?? this.status,
      messagesProcessed: messagesProcessed ?? this.messagesProcessed,
      turnsCreated: turnsCreated ?? this.turnsCreated,
      entitiesExtracted: entitiesExtracted ?? this.entitiesExtracted,
      errorMessage: errorMessage ?? this.errorMessage,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (startedAt.present) {
      map['started_at'] = Variable<String>(startedAt.value);
    }
    if (completedAt.present) {
      map['completed_at'] = Variable<String>(completedAt.value);
    }
    if (status.present) {
      map['status'] = Variable<String>(status.value);
    }
    if (messagesProcessed.present) {
      map['messages_processed'] = Variable<int>(messagesProcessed.value);
    }
    if (turnsCreated.present) {
      map['turns_created'] = Variable<int>(turnsCreated.value);
    }
    if (entitiesExtracted.present) {
      map['entities_extracted'] = Variable<int>(entitiesExtracted.value);
    }
    if (errorMessage.present) {
      map['error_message'] = Variable<String>(errorMessage.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('PipelineRunsCompanion(')
          ..write('id: $id, ')
          ..write('startedAt: $startedAt, ')
          ..write('completedAt: $completedAt, ')
          ..write('status: $status, ')
          ..write('messagesProcessed: $messagesProcessed, ')
          ..write('turnsCreated: $turnsCreated, ')
          ..write('entitiesExtracted: $entitiesExtracted, ')
          ..write('errorMessage: $errorMessage')
          ..write(')'))
        .toString();
  }
}

class $SubjectSubjectsTable extends SubjectSubjects
    with TableInfo<$SubjectSubjectsTable, SubjectRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $SubjectSubjectsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
      'id', aliasedName, false,
      hasAutoIncrement: true,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('PRIMARY KEY AUTOINCREMENT'));
  static const VerificationMeta _civIdMeta = const VerificationMeta('civId');
  @override
  late final GeneratedColumn<int> civId = GeneratedColumn<int>(
      'civ_id', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _sourceTurnIdMeta =
      const VerificationMeta('sourceTurnId');
  @override
  late final GeneratedColumn<int> sourceTurnId = GeneratedColumn<int>(
      'source_turn_id', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _directionMeta =
      const VerificationMeta('direction');
  @override
  late final GeneratedColumn<String> direction = GeneratedColumn<String>(
      'direction', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _titleMeta = const VerificationMeta('title');
  @override
  late final GeneratedColumn<String> title = GeneratedColumn<String>(
      'title', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _descriptionMeta =
      const VerificationMeta('description');
  @override
  late final GeneratedColumn<String> description = GeneratedColumn<String>(
      'description', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _sourceQuoteMeta =
      const VerificationMeta('sourceQuote');
  @override
  late final GeneratedColumn<String> sourceQuote = GeneratedColumn<String>(
      'source_quote', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _categoryMeta =
      const VerificationMeta('category');
  @override
  late final GeneratedColumn<String> category = GeneratedColumn<String>(
      'category', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _statusMeta = const VerificationMeta('status');
  @override
  late final GeneratedColumn<String> status = GeneratedColumn<String>(
      'status', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('open'));
  static const VerificationMeta _tagsMeta = const VerificationMeta('tags');
  @override
  late final GeneratedColumn<String> tags = GeneratedColumn<String>(
      'tags', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('[]'));
  static const VerificationMeta _createdAtMeta =
      const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
      'created_at', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _updatedAtMeta =
      const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<String> updatedAt = GeneratedColumn<String>(
      'updated_at', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  @override
  List<GeneratedColumn> get $columns => [
        id,
        civId,
        sourceTurnId,
        direction,
        title,
        description,
        sourceQuote,
        category,
        status,
        tags,
        createdAt,
        updatedAt
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'subject_subjects';
  @override
  VerificationContext validateIntegrity(Insertable<SubjectRow> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('civ_id')) {
      context.handle(
          _civIdMeta, civId.isAcceptableOrUnknown(data['civ_id']!, _civIdMeta));
    } else if (isInserting) {
      context.missing(_civIdMeta);
    }
    if (data.containsKey('source_turn_id')) {
      context.handle(
          _sourceTurnIdMeta,
          sourceTurnId.isAcceptableOrUnknown(
              data['source_turn_id']!, _sourceTurnIdMeta));
    }
    if (data.containsKey('direction')) {
      context.handle(_directionMeta,
          direction.isAcceptableOrUnknown(data['direction']!, _directionMeta));
    } else if (isInserting) {
      context.missing(_directionMeta);
    }
    if (data.containsKey('title')) {
      context.handle(
          _titleMeta, title.isAcceptableOrUnknown(data['title']!, _titleMeta));
    } else if (isInserting) {
      context.missing(_titleMeta);
    }
    if (data.containsKey('description')) {
      context.handle(
          _descriptionMeta,
          description.isAcceptableOrUnknown(
              data['description']!, _descriptionMeta));
    }
    if (data.containsKey('source_quote')) {
      context.handle(
          _sourceQuoteMeta,
          sourceQuote.isAcceptableOrUnknown(
              data['source_quote']!, _sourceQuoteMeta));
    }
    if (data.containsKey('category')) {
      context.handle(_categoryMeta,
          category.isAcceptableOrUnknown(data['category']!, _categoryMeta));
    } else if (isInserting) {
      context.missing(_categoryMeta);
    }
    if (data.containsKey('status')) {
      context.handle(_statusMeta,
          status.isAcceptableOrUnknown(data['status']!, _statusMeta));
    }
    if (data.containsKey('tags')) {
      context.handle(
          _tagsMeta, tags.isAcceptableOrUnknown(data['tags']!, _tagsMeta));
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta,
          createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta,
          updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  SubjectRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return SubjectRow(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}id'])!,
      civId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}civ_id'])!,
      sourceTurnId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}source_turn_id']),
      direction: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}direction'])!,
      title: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}title'])!,
      description: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}description']),
      sourceQuote: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}source_quote']),
      category: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}category'])!,
      status: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}status'])!,
      tags: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}tags'])!,
      createdAt: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}created_at'])!,
      updatedAt: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}updated_at'])!,
    );
  }

  @override
  $SubjectSubjectsTable createAlias(String alias) {
    return $SubjectSubjectsTable(attachedDatabase, alias);
  }
}

class SubjectRow extends DataClass implements Insertable<SubjectRow> {
  final int id;
  final int civId;

  /// Nullable: NULL for GM-created subjects not tied to a specific pipeline turn.
  final int? sourceTurnId;

  /// 'mj_to_pj' = GM poses a choice; 'pj_to_mj' = player takes an initiative
  final String direction;
  final String title;
  final String? description;

  /// Verbatim phrase from the source turn text — used for auto-highlight on navigation.
  final String? sourceQuote;

  /// 'choice' | 'question' | 'initiative' | 'request'
  final String category;

  /// 'open' | 'resolved' | 'superseded' | 'abandoned'
  final String status;

  /// JSON array of domain tags auto-assigned by the pipeline, e.g. ["militaire","politique"]
  final String tags;
  final String createdAt;
  final String updatedAt;
  const SubjectRow(
      {required this.id,
      required this.civId,
      this.sourceTurnId,
      required this.direction,
      required this.title,
      this.description,
      this.sourceQuote,
      required this.category,
      required this.status,
      required this.tags,
      required this.createdAt,
      required this.updatedAt});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['civ_id'] = Variable<int>(civId);
    if (!nullToAbsent || sourceTurnId != null) {
      map['source_turn_id'] = Variable<int>(sourceTurnId);
    }
    map['direction'] = Variable<String>(direction);
    map['title'] = Variable<String>(title);
    if (!nullToAbsent || description != null) {
      map['description'] = Variable<String>(description);
    }
    if (!nullToAbsent || sourceQuote != null) {
      map['source_quote'] = Variable<String>(sourceQuote);
    }
    map['category'] = Variable<String>(category);
    map['status'] = Variable<String>(status);
    map['tags'] = Variable<String>(tags);
    map['created_at'] = Variable<String>(createdAt);
    map['updated_at'] = Variable<String>(updatedAt);
    return map;
  }

  SubjectSubjectsCompanion toCompanion(bool nullToAbsent) {
    return SubjectSubjectsCompanion(
      id: Value(id),
      civId: Value(civId),
      sourceTurnId: sourceTurnId == null && nullToAbsent
          ? const Value.absent()
          : Value(sourceTurnId),
      direction: Value(direction),
      title: Value(title),
      description: description == null && nullToAbsent
          ? const Value.absent()
          : Value(description),
      sourceQuote: sourceQuote == null && nullToAbsent
          ? const Value.absent()
          : Value(sourceQuote),
      category: Value(category),
      status: Value(status),
      tags: Value(tags),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
    );
  }

  factory SubjectRow.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return SubjectRow(
      id: serializer.fromJson<int>(json['id']),
      civId: serializer.fromJson<int>(json['civId']),
      sourceTurnId: serializer.fromJson<int?>(json['sourceTurnId']),
      direction: serializer.fromJson<String>(json['direction']),
      title: serializer.fromJson<String>(json['title']),
      description: serializer.fromJson<String?>(json['description']),
      sourceQuote: serializer.fromJson<String?>(json['sourceQuote']),
      category: serializer.fromJson<String>(json['category']),
      status: serializer.fromJson<String>(json['status']),
      tags: serializer.fromJson<String>(json['tags']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
      updatedAt: serializer.fromJson<String>(json['updatedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'civId': serializer.toJson<int>(civId),
      'sourceTurnId': serializer.toJson<int?>(sourceTurnId),
      'direction': serializer.toJson<String>(direction),
      'title': serializer.toJson<String>(title),
      'description': serializer.toJson<String?>(description),
      'sourceQuote': serializer.toJson<String?>(sourceQuote),
      'category': serializer.toJson<String>(category),
      'status': serializer.toJson<String>(status),
      'tags': serializer.toJson<String>(tags),
      'createdAt': serializer.toJson<String>(createdAt),
      'updatedAt': serializer.toJson<String>(updatedAt),
    };
  }

  SubjectRow copyWith(
          {int? id,
          int? civId,
          Value<int?> sourceTurnId = const Value.absent(),
          String? direction,
          String? title,
          Value<String?> description = const Value.absent(),
          Value<String?> sourceQuote = const Value.absent(),
          String? category,
          String? status,
          String? tags,
          String? createdAt,
          String? updatedAt}) =>
      SubjectRow(
        id: id ?? this.id,
        civId: civId ?? this.civId,
        sourceTurnId:
            sourceTurnId.present ? sourceTurnId.value : this.sourceTurnId,
        direction: direction ?? this.direction,
        title: title ?? this.title,
        description: description.present ? description.value : this.description,
        sourceQuote: sourceQuote.present ? sourceQuote.value : this.sourceQuote,
        category: category ?? this.category,
        status: status ?? this.status,
        tags: tags ?? this.tags,
        createdAt: createdAt ?? this.createdAt,
        updatedAt: updatedAt ?? this.updatedAt,
      );
  SubjectRow copyWithCompanion(SubjectSubjectsCompanion data) {
    return SubjectRow(
      id: data.id.present ? data.id.value : this.id,
      civId: data.civId.present ? data.civId.value : this.civId,
      sourceTurnId: data.sourceTurnId.present
          ? data.sourceTurnId.value
          : this.sourceTurnId,
      direction: data.direction.present ? data.direction.value : this.direction,
      title: data.title.present ? data.title.value : this.title,
      description:
          data.description.present ? data.description.value : this.description,
      sourceQuote:
          data.sourceQuote.present ? data.sourceQuote.value : this.sourceQuote,
      category: data.category.present ? data.category.value : this.category,
      status: data.status.present ? data.status.value : this.status,
      tags: data.tags.present ? data.tags.value : this.tags,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('SubjectRow(')
          ..write('id: $id, ')
          ..write('civId: $civId, ')
          ..write('sourceTurnId: $sourceTurnId, ')
          ..write('direction: $direction, ')
          ..write('title: $title, ')
          ..write('description: $description, ')
          ..write('sourceQuote: $sourceQuote, ')
          ..write('category: $category, ')
          ..write('status: $status, ')
          ..write('tags: $tags, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, civId, sourceTurnId, direction, title,
      description, sourceQuote, category, status, tags, createdAt, updatedAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is SubjectRow &&
          other.id == this.id &&
          other.civId == this.civId &&
          other.sourceTurnId == this.sourceTurnId &&
          other.direction == this.direction &&
          other.title == this.title &&
          other.description == this.description &&
          other.sourceQuote == this.sourceQuote &&
          other.category == this.category &&
          other.status == this.status &&
          other.tags == this.tags &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt);
}

class SubjectSubjectsCompanion extends UpdateCompanion<SubjectRow> {
  final Value<int> id;
  final Value<int> civId;
  final Value<int?> sourceTurnId;
  final Value<String> direction;
  final Value<String> title;
  final Value<String?> description;
  final Value<String?> sourceQuote;
  final Value<String> category;
  final Value<String> status;
  final Value<String> tags;
  final Value<String> createdAt;
  final Value<String> updatedAt;
  const SubjectSubjectsCompanion({
    this.id = const Value.absent(),
    this.civId = const Value.absent(),
    this.sourceTurnId = const Value.absent(),
    this.direction = const Value.absent(),
    this.title = const Value.absent(),
    this.description = const Value.absent(),
    this.sourceQuote = const Value.absent(),
    this.category = const Value.absent(),
    this.status = const Value.absent(),
    this.tags = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
  });
  SubjectSubjectsCompanion.insert({
    this.id = const Value.absent(),
    required int civId,
    this.sourceTurnId = const Value.absent(),
    required String direction,
    required String title,
    this.description = const Value.absent(),
    this.sourceQuote = const Value.absent(),
    required String category,
    this.status = const Value.absent(),
    this.tags = const Value.absent(),
    required String createdAt,
    required String updatedAt,
  })  : civId = Value(civId),
        direction = Value(direction),
        title = Value(title),
        category = Value(category),
        createdAt = Value(createdAt),
        updatedAt = Value(updatedAt);
  static Insertable<SubjectRow> custom({
    Expression<int>? id,
    Expression<int>? civId,
    Expression<int>? sourceTurnId,
    Expression<String>? direction,
    Expression<String>? title,
    Expression<String>? description,
    Expression<String>? sourceQuote,
    Expression<String>? category,
    Expression<String>? status,
    Expression<String>? tags,
    Expression<String>? createdAt,
    Expression<String>? updatedAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (civId != null) 'civ_id': civId,
      if (sourceTurnId != null) 'source_turn_id': sourceTurnId,
      if (direction != null) 'direction': direction,
      if (title != null) 'title': title,
      if (description != null) 'description': description,
      if (sourceQuote != null) 'source_quote': sourceQuote,
      if (category != null) 'category': category,
      if (status != null) 'status': status,
      if (tags != null) 'tags': tags,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
    });
  }

  SubjectSubjectsCompanion copyWith(
      {Value<int>? id,
      Value<int>? civId,
      Value<int?>? sourceTurnId,
      Value<String>? direction,
      Value<String>? title,
      Value<String?>? description,
      Value<String?>? sourceQuote,
      Value<String>? category,
      Value<String>? status,
      Value<String>? tags,
      Value<String>? createdAt,
      Value<String>? updatedAt}) {
    return SubjectSubjectsCompanion(
      id: id ?? this.id,
      civId: civId ?? this.civId,
      sourceTurnId: sourceTurnId ?? this.sourceTurnId,
      direction: direction ?? this.direction,
      title: title ?? this.title,
      description: description ?? this.description,
      sourceQuote: sourceQuote ?? this.sourceQuote,
      category: category ?? this.category,
      status: status ?? this.status,
      tags: tags ?? this.tags,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (civId.present) {
      map['civ_id'] = Variable<int>(civId.value);
    }
    if (sourceTurnId.present) {
      map['source_turn_id'] = Variable<int>(sourceTurnId.value);
    }
    if (direction.present) {
      map['direction'] = Variable<String>(direction.value);
    }
    if (title.present) {
      map['title'] = Variable<String>(title.value);
    }
    if (description.present) {
      map['description'] = Variable<String>(description.value);
    }
    if (sourceQuote.present) {
      map['source_quote'] = Variable<String>(sourceQuote.value);
    }
    if (category.present) {
      map['category'] = Variable<String>(category.value);
    }
    if (status.present) {
      map['status'] = Variable<String>(status.value);
    }
    if (tags.present) {
      map['tags'] = Variable<String>(tags.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<String>(updatedAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('SubjectSubjectsCompanion(')
          ..write('id: $id, ')
          ..write('civId: $civId, ')
          ..write('sourceTurnId: $sourceTurnId, ')
          ..write('direction: $direction, ')
          ..write('title: $title, ')
          ..write('description: $description, ')
          ..write('sourceQuote: $sourceQuote, ')
          ..write('category: $category, ')
          ..write('status: $status, ')
          ..write('tags: $tags, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }
}

class $SubjectOptionsTable extends SubjectOptions
    with TableInfo<$SubjectOptionsTable, SubjectOptionRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $SubjectOptionsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
      'id', aliasedName, false,
      hasAutoIncrement: true,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('PRIMARY KEY AUTOINCREMENT'));
  static const VerificationMeta _subjectIdMeta =
      const VerificationMeta('subjectId');
  @override
  late final GeneratedColumn<int> subjectId = GeneratedColumn<int>(
      'subject_id', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _optionNumberMeta =
      const VerificationMeta('optionNumber');
  @override
  late final GeneratedColumn<int> optionNumber = GeneratedColumn<int>(
      'option_number', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _labelMeta = const VerificationMeta('label');
  @override
  late final GeneratedColumn<String> label = GeneratedColumn<String>(
      'label', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _descriptionMeta =
      const VerificationMeta('description');
  @override
  late final GeneratedColumn<String> description = GeneratedColumn<String>(
      'description', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _isLibreMeta =
      const VerificationMeta('isLibre');
  @override
  late final GeneratedColumn<bool> isLibre = GeneratedColumn<bool>(
      'is_libre', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_libre" IN (0, 1))'),
      defaultValue: const Constant(false));
  @override
  List<GeneratedColumn> get $columns =>
      [id, subjectId, optionNumber, label, description, isLibre];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'subject_options';
  @override
  VerificationContext validateIntegrity(Insertable<SubjectOptionRow> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('subject_id')) {
      context.handle(_subjectIdMeta,
          subjectId.isAcceptableOrUnknown(data['subject_id']!, _subjectIdMeta));
    } else if (isInserting) {
      context.missing(_subjectIdMeta);
    }
    if (data.containsKey('option_number')) {
      context.handle(
          _optionNumberMeta,
          optionNumber.isAcceptableOrUnknown(
              data['option_number']!, _optionNumberMeta));
    } else if (isInserting) {
      context.missing(_optionNumberMeta);
    }
    if (data.containsKey('label')) {
      context.handle(
          _labelMeta, label.isAcceptableOrUnknown(data['label']!, _labelMeta));
    } else if (isInserting) {
      context.missing(_labelMeta);
    }
    if (data.containsKey('description')) {
      context.handle(
          _descriptionMeta,
          description.isAcceptableOrUnknown(
              data['description']!, _descriptionMeta));
    }
    if (data.containsKey('is_libre')) {
      context.handle(_isLibreMeta,
          isLibre.isAcceptableOrUnknown(data['is_libre']!, _isLibreMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  SubjectOptionRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return SubjectOptionRow(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}id'])!,
      subjectId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}subject_id'])!,
      optionNumber: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}option_number'])!,
      label: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}label'])!,
      description: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}description']),
      isLibre: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_libre'])!,
    );
  }

  @override
  $SubjectOptionsTable createAlias(String alias) {
    return $SubjectOptionsTable(attachedDatabase, alias);
  }
}

class SubjectOptionRow extends DataClass
    implements Insertable<SubjectOptionRow> {
  final int id;
  final int subjectId;
  final int optionNumber;
  final String label;
  final String? description;

  /// 1 = free-form "libre" option
  final bool isLibre;
  const SubjectOptionRow(
      {required this.id,
      required this.subjectId,
      required this.optionNumber,
      required this.label,
      this.description,
      required this.isLibre});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['subject_id'] = Variable<int>(subjectId);
    map['option_number'] = Variable<int>(optionNumber);
    map['label'] = Variable<String>(label);
    if (!nullToAbsent || description != null) {
      map['description'] = Variable<String>(description);
    }
    map['is_libre'] = Variable<bool>(isLibre);
    return map;
  }

  SubjectOptionsCompanion toCompanion(bool nullToAbsent) {
    return SubjectOptionsCompanion(
      id: Value(id),
      subjectId: Value(subjectId),
      optionNumber: Value(optionNumber),
      label: Value(label),
      description: description == null && nullToAbsent
          ? const Value.absent()
          : Value(description),
      isLibre: Value(isLibre),
    );
  }

  factory SubjectOptionRow.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return SubjectOptionRow(
      id: serializer.fromJson<int>(json['id']),
      subjectId: serializer.fromJson<int>(json['subjectId']),
      optionNumber: serializer.fromJson<int>(json['optionNumber']),
      label: serializer.fromJson<String>(json['label']),
      description: serializer.fromJson<String?>(json['description']),
      isLibre: serializer.fromJson<bool>(json['isLibre']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'subjectId': serializer.toJson<int>(subjectId),
      'optionNumber': serializer.toJson<int>(optionNumber),
      'label': serializer.toJson<String>(label),
      'description': serializer.toJson<String?>(description),
      'isLibre': serializer.toJson<bool>(isLibre),
    };
  }

  SubjectOptionRow copyWith(
          {int? id,
          int? subjectId,
          int? optionNumber,
          String? label,
          Value<String?> description = const Value.absent(),
          bool? isLibre}) =>
      SubjectOptionRow(
        id: id ?? this.id,
        subjectId: subjectId ?? this.subjectId,
        optionNumber: optionNumber ?? this.optionNumber,
        label: label ?? this.label,
        description: description.present ? description.value : this.description,
        isLibre: isLibre ?? this.isLibre,
      );
  SubjectOptionRow copyWithCompanion(SubjectOptionsCompanion data) {
    return SubjectOptionRow(
      id: data.id.present ? data.id.value : this.id,
      subjectId: data.subjectId.present ? data.subjectId.value : this.subjectId,
      optionNumber: data.optionNumber.present
          ? data.optionNumber.value
          : this.optionNumber,
      label: data.label.present ? data.label.value : this.label,
      description:
          data.description.present ? data.description.value : this.description,
      isLibre: data.isLibre.present ? data.isLibre.value : this.isLibre,
    );
  }

  @override
  String toString() {
    return (StringBuffer('SubjectOptionRow(')
          ..write('id: $id, ')
          ..write('subjectId: $subjectId, ')
          ..write('optionNumber: $optionNumber, ')
          ..write('label: $label, ')
          ..write('description: $description, ')
          ..write('isLibre: $isLibre')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode =>
      Object.hash(id, subjectId, optionNumber, label, description, isLibre);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is SubjectOptionRow &&
          other.id == this.id &&
          other.subjectId == this.subjectId &&
          other.optionNumber == this.optionNumber &&
          other.label == this.label &&
          other.description == this.description &&
          other.isLibre == this.isLibre);
}

class SubjectOptionsCompanion extends UpdateCompanion<SubjectOptionRow> {
  final Value<int> id;
  final Value<int> subjectId;
  final Value<int> optionNumber;
  final Value<String> label;
  final Value<String?> description;
  final Value<bool> isLibre;
  const SubjectOptionsCompanion({
    this.id = const Value.absent(),
    this.subjectId = const Value.absent(),
    this.optionNumber = const Value.absent(),
    this.label = const Value.absent(),
    this.description = const Value.absent(),
    this.isLibre = const Value.absent(),
  });
  SubjectOptionsCompanion.insert({
    this.id = const Value.absent(),
    required int subjectId,
    required int optionNumber,
    required String label,
    this.description = const Value.absent(),
    this.isLibre = const Value.absent(),
  })  : subjectId = Value(subjectId),
        optionNumber = Value(optionNumber),
        label = Value(label);
  static Insertable<SubjectOptionRow> custom({
    Expression<int>? id,
    Expression<int>? subjectId,
    Expression<int>? optionNumber,
    Expression<String>? label,
    Expression<String>? description,
    Expression<bool>? isLibre,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (subjectId != null) 'subject_id': subjectId,
      if (optionNumber != null) 'option_number': optionNumber,
      if (label != null) 'label': label,
      if (description != null) 'description': description,
      if (isLibre != null) 'is_libre': isLibre,
    });
  }

  SubjectOptionsCompanion copyWith(
      {Value<int>? id,
      Value<int>? subjectId,
      Value<int>? optionNumber,
      Value<String>? label,
      Value<String?>? description,
      Value<bool>? isLibre}) {
    return SubjectOptionsCompanion(
      id: id ?? this.id,
      subjectId: subjectId ?? this.subjectId,
      optionNumber: optionNumber ?? this.optionNumber,
      label: label ?? this.label,
      description: description ?? this.description,
      isLibre: isLibre ?? this.isLibre,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (subjectId.present) {
      map['subject_id'] = Variable<int>(subjectId.value);
    }
    if (optionNumber.present) {
      map['option_number'] = Variable<int>(optionNumber.value);
    }
    if (label.present) {
      map['label'] = Variable<String>(label.value);
    }
    if (description.present) {
      map['description'] = Variable<String>(description.value);
    }
    if (isLibre.present) {
      map['is_libre'] = Variable<bool>(isLibre.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('SubjectOptionsCompanion(')
          ..write('id: $id, ')
          ..write('subjectId: $subjectId, ')
          ..write('optionNumber: $optionNumber, ')
          ..write('label: $label, ')
          ..write('description: $description, ')
          ..write('isLibre: $isLibre')
          ..write(')'))
        .toString();
  }
}

class $SubjectResolutionsTable extends SubjectResolutions
    with TableInfo<$SubjectResolutionsTable, SubjectResolutionRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $SubjectResolutionsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
      'id', aliasedName, false,
      hasAutoIncrement: true,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('PRIMARY KEY AUTOINCREMENT'));
  static const VerificationMeta _subjectIdMeta =
      const VerificationMeta('subjectId');
  @override
  late final GeneratedColumn<int> subjectId = GeneratedColumn<int>(
      'subject_id', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _resolvedByTurnIdMeta =
      const VerificationMeta('resolvedByTurnId');
  @override
  late final GeneratedColumn<int> resolvedByTurnId = GeneratedColumn<int>(
      'resolved_by_turn_id', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _chosenOptionIdMeta =
      const VerificationMeta('chosenOptionId');
  @override
  late final GeneratedColumn<int> chosenOptionId = GeneratedColumn<int>(
      'chosen_option_id', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _resolutionTextMeta =
      const VerificationMeta('resolutionText');
  @override
  late final GeneratedColumn<String> resolutionText = GeneratedColumn<String>(
      'resolution_text', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _sourceQuoteMeta =
      const VerificationMeta('sourceQuote');
  @override
  late final GeneratedColumn<String> sourceQuote = GeneratedColumn<String>(
      'source_quote', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _isLibreMeta =
      const VerificationMeta('isLibre');
  @override
  late final GeneratedColumn<bool> isLibre = GeneratedColumn<bool>(
      'is_libre', aliasedName, false,
      type: DriftSqlType.bool,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('CHECK ("is_libre" IN (0, 1))'),
      defaultValue: const Constant(false));
  static const VerificationMeta _confidenceMeta =
      const VerificationMeta('confidence');
  @override
  late final GeneratedColumn<double> confidence = GeneratedColumn<double>(
      'confidence', aliasedName, false,
      type: DriftSqlType.double,
      requiredDuringInsert: false,
      defaultValue: const Constant(0.0));
  static const VerificationMeta _createdAtMeta =
      const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
      'created_at', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  @override
  List<GeneratedColumn> get $columns => [
        id,
        subjectId,
        resolvedByTurnId,
        chosenOptionId,
        resolutionText,
        sourceQuote,
        isLibre,
        confidence,
        createdAt
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'subject_resolutions';
  @override
  VerificationContext validateIntegrity(
      Insertable<SubjectResolutionRow> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('subject_id')) {
      context.handle(_subjectIdMeta,
          subjectId.isAcceptableOrUnknown(data['subject_id']!, _subjectIdMeta));
    } else if (isInserting) {
      context.missing(_subjectIdMeta);
    }
    if (data.containsKey('resolved_by_turn_id')) {
      context.handle(
          _resolvedByTurnIdMeta,
          resolvedByTurnId.isAcceptableOrUnknown(
              data['resolved_by_turn_id']!, _resolvedByTurnIdMeta));
    } else if (isInserting) {
      context.missing(_resolvedByTurnIdMeta);
    }
    if (data.containsKey('chosen_option_id')) {
      context.handle(
          _chosenOptionIdMeta,
          chosenOptionId.isAcceptableOrUnknown(
              data['chosen_option_id']!, _chosenOptionIdMeta));
    }
    if (data.containsKey('resolution_text')) {
      context.handle(
          _resolutionTextMeta,
          resolutionText.isAcceptableOrUnknown(
              data['resolution_text']!, _resolutionTextMeta));
    } else if (isInserting) {
      context.missing(_resolutionTextMeta);
    }
    if (data.containsKey('source_quote')) {
      context.handle(
          _sourceQuoteMeta,
          sourceQuote.isAcceptableOrUnknown(
              data['source_quote']!, _sourceQuoteMeta));
    }
    if (data.containsKey('is_libre')) {
      context.handle(_isLibreMeta,
          isLibre.isAcceptableOrUnknown(data['is_libre']!, _isLibreMeta));
    }
    if (data.containsKey('confidence')) {
      context.handle(
          _confidenceMeta,
          confidence.isAcceptableOrUnknown(
              data['confidence']!, _confidenceMeta));
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta,
          createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  SubjectResolutionRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return SubjectResolutionRow(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}id'])!,
      subjectId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}subject_id'])!,
      resolvedByTurnId: attachedDatabase.typeMapping.read(
          DriftSqlType.int, data['${effectivePrefix}resolved_by_turn_id'])!,
      chosenOptionId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}chosen_option_id']),
      resolutionText: attachedDatabase.typeMapping.read(
          DriftSqlType.string, data['${effectivePrefix}resolution_text'])!,
      sourceQuote: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}source_quote']),
      isLibre: attachedDatabase.typeMapping
          .read(DriftSqlType.bool, data['${effectivePrefix}is_libre'])!,
      confidence: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}confidence'])!,
      createdAt: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}created_at'])!,
    );
  }

  @override
  $SubjectResolutionsTable createAlias(String alias) {
    return $SubjectResolutionsTable(attachedDatabase, alias);
  }
}

class SubjectResolutionRow extends DataClass
    implements Insertable<SubjectResolutionRow> {
  final int id;
  final int subjectId;
  final int resolvedByTurnId;
  final int? chosenOptionId;
  final String resolutionText;

  /// Verbatim phrase from the player/GM text — used for auto-highlight on navigation.
  final String? sourceQuote;

  /// 1 = player chose the free-form "libre" option
  final bool isLibre;

  /// 0.0 – 1.0 confidence score from the LLM
  final double confidence;
  final String createdAt;
  const SubjectResolutionRow(
      {required this.id,
      required this.subjectId,
      required this.resolvedByTurnId,
      this.chosenOptionId,
      required this.resolutionText,
      this.sourceQuote,
      required this.isLibre,
      required this.confidence,
      required this.createdAt});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['subject_id'] = Variable<int>(subjectId);
    map['resolved_by_turn_id'] = Variable<int>(resolvedByTurnId);
    if (!nullToAbsent || chosenOptionId != null) {
      map['chosen_option_id'] = Variable<int>(chosenOptionId);
    }
    map['resolution_text'] = Variable<String>(resolutionText);
    if (!nullToAbsent || sourceQuote != null) {
      map['source_quote'] = Variable<String>(sourceQuote);
    }
    map['is_libre'] = Variable<bool>(isLibre);
    map['confidence'] = Variable<double>(confidence);
    map['created_at'] = Variable<String>(createdAt);
    return map;
  }

  SubjectResolutionsCompanion toCompanion(bool nullToAbsent) {
    return SubjectResolutionsCompanion(
      id: Value(id),
      subjectId: Value(subjectId),
      resolvedByTurnId: Value(resolvedByTurnId),
      chosenOptionId: chosenOptionId == null && nullToAbsent
          ? const Value.absent()
          : Value(chosenOptionId),
      resolutionText: Value(resolutionText),
      sourceQuote: sourceQuote == null && nullToAbsent
          ? const Value.absent()
          : Value(sourceQuote),
      isLibre: Value(isLibre),
      confidence: Value(confidence),
      createdAt: Value(createdAt),
    );
  }

  factory SubjectResolutionRow.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return SubjectResolutionRow(
      id: serializer.fromJson<int>(json['id']),
      subjectId: serializer.fromJson<int>(json['subjectId']),
      resolvedByTurnId: serializer.fromJson<int>(json['resolvedByTurnId']),
      chosenOptionId: serializer.fromJson<int?>(json['chosenOptionId']),
      resolutionText: serializer.fromJson<String>(json['resolutionText']),
      sourceQuote: serializer.fromJson<String?>(json['sourceQuote']),
      isLibre: serializer.fromJson<bool>(json['isLibre']),
      confidence: serializer.fromJson<double>(json['confidence']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'subjectId': serializer.toJson<int>(subjectId),
      'resolvedByTurnId': serializer.toJson<int>(resolvedByTurnId),
      'chosenOptionId': serializer.toJson<int?>(chosenOptionId),
      'resolutionText': serializer.toJson<String>(resolutionText),
      'sourceQuote': serializer.toJson<String?>(sourceQuote),
      'isLibre': serializer.toJson<bool>(isLibre),
      'confidence': serializer.toJson<double>(confidence),
      'createdAt': serializer.toJson<String>(createdAt),
    };
  }

  SubjectResolutionRow copyWith(
          {int? id,
          int? subjectId,
          int? resolvedByTurnId,
          Value<int?> chosenOptionId = const Value.absent(),
          String? resolutionText,
          Value<String?> sourceQuote = const Value.absent(),
          bool? isLibre,
          double? confidence,
          String? createdAt}) =>
      SubjectResolutionRow(
        id: id ?? this.id,
        subjectId: subjectId ?? this.subjectId,
        resolvedByTurnId: resolvedByTurnId ?? this.resolvedByTurnId,
        chosenOptionId:
            chosenOptionId.present ? chosenOptionId.value : this.chosenOptionId,
        resolutionText: resolutionText ?? this.resolutionText,
        sourceQuote: sourceQuote.present ? sourceQuote.value : this.sourceQuote,
        isLibre: isLibre ?? this.isLibre,
        confidence: confidence ?? this.confidence,
        createdAt: createdAt ?? this.createdAt,
      );
  SubjectResolutionRow copyWithCompanion(SubjectResolutionsCompanion data) {
    return SubjectResolutionRow(
      id: data.id.present ? data.id.value : this.id,
      subjectId: data.subjectId.present ? data.subjectId.value : this.subjectId,
      resolvedByTurnId: data.resolvedByTurnId.present
          ? data.resolvedByTurnId.value
          : this.resolvedByTurnId,
      chosenOptionId: data.chosenOptionId.present
          ? data.chosenOptionId.value
          : this.chosenOptionId,
      resolutionText: data.resolutionText.present
          ? data.resolutionText.value
          : this.resolutionText,
      sourceQuote:
          data.sourceQuote.present ? data.sourceQuote.value : this.sourceQuote,
      isLibre: data.isLibre.present ? data.isLibre.value : this.isLibre,
      confidence:
          data.confidence.present ? data.confidence.value : this.confidence,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('SubjectResolutionRow(')
          ..write('id: $id, ')
          ..write('subjectId: $subjectId, ')
          ..write('resolvedByTurnId: $resolvedByTurnId, ')
          ..write('chosenOptionId: $chosenOptionId, ')
          ..write('resolutionText: $resolutionText, ')
          ..write('sourceQuote: $sourceQuote, ')
          ..write('isLibre: $isLibre, ')
          ..write('confidence: $confidence, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
      id,
      subjectId,
      resolvedByTurnId,
      chosenOptionId,
      resolutionText,
      sourceQuote,
      isLibre,
      confidence,
      createdAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is SubjectResolutionRow &&
          other.id == this.id &&
          other.subjectId == this.subjectId &&
          other.resolvedByTurnId == this.resolvedByTurnId &&
          other.chosenOptionId == this.chosenOptionId &&
          other.resolutionText == this.resolutionText &&
          other.sourceQuote == this.sourceQuote &&
          other.isLibre == this.isLibre &&
          other.confidence == this.confidence &&
          other.createdAt == this.createdAt);
}

class SubjectResolutionsCompanion
    extends UpdateCompanion<SubjectResolutionRow> {
  final Value<int> id;
  final Value<int> subjectId;
  final Value<int> resolvedByTurnId;
  final Value<int?> chosenOptionId;
  final Value<String> resolutionText;
  final Value<String?> sourceQuote;
  final Value<bool> isLibre;
  final Value<double> confidence;
  final Value<String> createdAt;
  const SubjectResolutionsCompanion({
    this.id = const Value.absent(),
    this.subjectId = const Value.absent(),
    this.resolvedByTurnId = const Value.absent(),
    this.chosenOptionId = const Value.absent(),
    this.resolutionText = const Value.absent(),
    this.sourceQuote = const Value.absent(),
    this.isLibre = const Value.absent(),
    this.confidence = const Value.absent(),
    this.createdAt = const Value.absent(),
  });
  SubjectResolutionsCompanion.insert({
    this.id = const Value.absent(),
    required int subjectId,
    required int resolvedByTurnId,
    this.chosenOptionId = const Value.absent(),
    required String resolutionText,
    this.sourceQuote = const Value.absent(),
    this.isLibre = const Value.absent(),
    this.confidence = const Value.absent(),
    required String createdAt,
  })  : subjectId = Value(subjectId),
        resolvedByTurnId = Value(resolvedByTurnId),
        resolutionText = Value(resolutionText),
        createdAt = Value(createdAt);
  static Insertable<SubjectResolutionRow> custom({
    Expression<int>? id,
    Expression<int>? subjectId,
    Expression<int>? resolvedByTurnId,
    Expression<int>? chosenOptionId,
    Expression<String>? resolutionText,
    Expression<String>? sourceQuote,
    Expression<bool>? isLibre,
    Expression<double>? confidence,
    Expression<String>? createdAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (subjectId != null) 'subject_id': subjectId,
      if (resolvedByTurnId != null) 'resolved_by_turn_id': resolvedByTurnId,
      if (chosenOptionId != null) 'chosen_option_id': chosenOptionId,
      if (resolutionText != null) 'resolution_text': resolutionText,
      if (sourceQuote != null) 'source_quote': sourceQuote,
      if (isLibre != null) 'is_libre': isLibre,
      if (confidence != null) 'confidence': confidence,
      if (createdAt != null) 'created_at': createdAt,
    });
  }

  SubjectResolutionsCompanion copyWith(
      {Value<int>? id,
      Value<int>? subjectId,
      Value<int>? resolvedByTurnId,
      Value<int?>? chosenOptionId,
      Value<String>? resolutionText,
      Value<String?>? sourceQuote,
      Value<bool>? isLibre,
      Value<double>? confidence,
      Value<String>? createdAt}) {
    return SubjectResolutionsCompanion(
      id: id ?? this.id,
      subjectId: subjectId ?? this.subjectId,
      resolvedByTurnId: resolvedByTurnId ?? this.resolvedByTurnId,
      chosenOptionId: chosenOptionId ?? this.chosenOptionId,
      resolutionText: resolutionText ?? this.resolutionText,
      sourceQuote: sourceQuote ?? this.sourceQuote,
      isLibre: isLibre ?? this.isLibre,
      confidence: confidence ?? this.confidence,
      createdAt: createdAt ?? this.createdAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (subjectId.present) {
      map['subject_id'] = Variable<int>(subjectId.value);
    }
    if (resolvedByTurnId.present) {
      map['resolved_by_turn_id'] = Variable<int>(resolvedByTurnId.value);
    }
    if (chosenOptionId.present) {
      map['chosen_option_id'] = Variable<int>(chosenOptionId.value);
    }
    if (resolutionText.present) {
      map['resolution_text'] = Variable<String>(resolutionText.value);
    }
    if (sourceQuote.present) {
      map['source_quote'] = Variable<String>(sourceQuote.value);
    }
    if (isLibre.present) {
      map['is_libre'] = Variable<bool>(isLibre.value);
    }
    if (confidence.present) {
      map['confidence'] = Variable<double>(confidence.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('SubjectResolutionsCompanion(')
          ..write('id: $id, ')
          ..write('subjectId: $subjectId, ')
          ..write('resolvedByTurnId: $resolvedByTurnId, ')
          ..write('chosenOptionId: $chosenOptionId, ')
          ..write('resolutionText: $resolutionText, ')
          ..write('sourceQuote: $sourceQuote, ')
          ..write('isLibre: $isLibre, ')
          ..write('confidence: $confidence, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }
}

class $NotesTable extends Notes with TableInfo<$NotesTable, NoteRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $NotesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
      'id', aliasedName, false,
      hasAutoIncrement: true,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('PRIMARY KEY AUTOINCREMENT'));
  static const VerificationMeta _entityIdMeta =
      const VerificationMeta('entityId');
  @override
  late final GeneratedColumn<int> entityId = GeneratedColumn<int>(
      'entity_id', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _subjectIdMeta =
      const VerificationMeta('subjectId');
  @override
  late final GeneratedColumn<int> subjectId = GeneratedColumn<int>(
      'subject_id', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _turnIdMeta = const VerificationMeta('turnId');
  @override
  late final GeneratedColumn<int> turnId = GeneratedColumn<int>(
      'turn_id', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _civIdMeta = const VerificationMeta('civId');
  @override
  late final GeneratedColumn<int> civId = GeneratedColumn<int>(
      'civ_id', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _titleMeta = const VerificationMeta('title');
  @override
  late final GeneratedColumn<String> title = GeneratedColumn<String>(
      'title', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant(''));
  static const VerificationMeta _contentMeta =
      const VerificationMeta('content');
  @override
  late final GeneratedColumn<String> content = GeneratedColumn<String>(
      'content', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant(''));
  static const VerificationMeta _pinnedMeta = const VerificationMeta('pinned');
  @override
  late final GeneratedColumn<int> pinned = GeneratedColumn<int>(
      'pinned', aliasedName, false,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultValue: const Constant(0));
  static const VerificationMeta _noteTypeMeta =
      const VerificationMeta('noteType');
  @override
  late final GeneratedColumn<String> noteType = GeneratedColumn<String>(
      'note_type', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('gm'));
  static const VerificationMeta _createdAtMeta =
      const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
      'created_at', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _updatedAtMeta =
      const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<String> updatedAt = GeneratedColumn<String>(
      'updated_at', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  @override
  List<GeneratedColumn> get $columns => [
        id,
        entityId,
        subjectId,
        turnId,
        civId,
        title,
        content,
        pinned,
        noteType,
        createdAt,
        updatedAt
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'notes';
  @override
  VerificationContext validateIntegrity(Insertable<NoteRow> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('entity_id')) {
      context.handle(_entityIdMeta,
          entityId.isAcceptableOrUnknown(data['entity_id']!, _entityIdMeta));
    }
    if (data.containsKey('subject_id')) {
      context.handle(_subjectIdMeta,
          subjectId.isAcceptableOrUnknown(data['subject_id']!, _subjectIdMeta));
    }
    if (data.containsKey('turn_id')) {
      context.handle(_turnIdMeta,
          turnId.isAcceptableOrUnknown(data['turn_id']!, _turnIdMeta));
    }
    if (data.containsKey('civ_id')) {
      context.handle(
          _civIdMeta, civId.isAcceptableOrUnknown(data['civ_id']!, _civIdMeta));
    }
    if (data.containsKey('title')) {
      context.handle(
          _titleMeta, title.isAcceptableOrUnknown(data['title']!, _titleMeta));
    }
    if (data.containsKey('content')) {
      context.handle(_contentMeta,
          content.isAcceptableOrUnknown(data['content']!, _contentMeta));
    }
    if (data.containsKey('pinned')) {
      context.handle(_pinnedMeta,
          pinned.isAcceptableOrUnknown(data['pinned']!, _pinnedMeta));
    }
    if (data.containsKey('note_type')) {
      context.handle(_noteTypeMeta,
          noteType.isAcceptableOrUnknown(data['note_type']!, _noteTypeMeta));
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta,
          createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta,
          updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  NoteRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return NoteRow(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}id'])!,
      entityId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}entity_id']),
      subjectId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}subject_id']),
      turnId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}turn_id']),
      civId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}civ_id']),
      title: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}title'])!,
      content: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}content'])!,
      pinned: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}pinned'])!,
      noteType: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}note_type'])!,
      createdAt: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}created_at'])!,
      updatedAt: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}updated_at'])!,
    );
  }

  @override
  $NotesTable createAlias(String alias) {
    return $NotesTable(attachedDatabase, alias);
  }
}

class NoteRow extends DataClass implements Insertable<NoteRow> {
  final int id;

  /// FK to entity_entities.id — null if note is on a subject or turn
  final int? entityId;

  /// FK to subject_subjects.id — null if note is on an entity or turn
  final int? subjectId;

  /// FK to turn_turns.id — null if note is on an entity or subject
  final int? turnId;

  /// FK to civ_civilizations.id — null if note is on an entity/subject/turn
  final int? civId;
  final String title;
  final String content;

  /// Whether this note should always be shown (even in compact tool output)
  final int pinned;

  /// 'gm' = GM annotation, 'agent' = injected into agent system prompt
  final String noteType;
  final String createdAt;
  final String updatedAt;
  const NoteRow(
      {required this.id,
      this.entityId,
      this.subjectId,
      this.turnId,
      this.civId,
      required this.title,
      required this.content,
      required this.pinned,
      required this.noteType,
      required this.createdAt,
      required this.updatedAt});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    if (!nullToAbsent || entityId != null) {
      map['entity_id'] = Variable<int>(entityId);
    }
    if (!nullToAbsent || subjectId != null) {
      map['subject_id'] = Variable<int>(subjectId);
    }
    if (!nullToAbsent || turnId != null) {
      map['turn_id'] = Variable<int>(turnId);
    }
    if (!nullToAbsent || civId != null) {
      map['civ_id'] = Variable<int>(civId);
    }
    map['title'] = Variable<String>(title);
    map['content'] = Variable<String>(content);
    map['pinned'] = Variable<int>(pinned);
    map['note_type'] = Variable<String>(noteType);
    map['created_at'] = Variable<String>(createdAt);
    map['updated_at'] = Variable<String>(updatedAt);
    return map;
  }

  NotesCompanion toCompanion(bool nullToAbsent) {
    return NotesCompanion(
      id: Value(id),
      entityId: entityId == null && nullToAbsent
          ? const Value.absent()
          : Value(entityId),
      subjectId: subjectId == null && nullToAbsent
          ? const Value.absent()
          : Value(subjectId),
      turnId:
          turnId == null && nullToAbsent ? const Value.absent() : Value(turnId),
      civId:
          civId == null && nullToAbsent ? const Value.absent() : Value(civId),
      title: Value(title),
      content: Value(content),
      pinned: Value(pinned),
      noteType: Value(noteType),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
    );
  }

  factory NoteRow.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return NoteRow(
      id: serializer.fromJson<int>(json['id']),
      entityId: serializer.fromJson<int?>(json['entityId']),
      subjectId: serializer.fromJson<int?>(json['subjectId']),
      turnId: serializer.fromJson<int?>(json['turnId']),
      civId: serializer.fromJson<int?>(json['civId']),
      title: serializer.fromJson<String>(json['title']),
      content: serializer.fromJson<String>(json['content']),
      pinned: serializer.fromJson<int>(json['pinned']),
      noteType: serializer.fromJson<String>(json['noteType']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
      updatedAt: serializer.fromJson<String>(json['updatedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'entityId': serializer.toJson<int?>(entityId),
      'subjectId': serializer.toJson<int?>(subjectId),
      'turnId': serializer.toJson<int?>(turnId),
      'civId': serializer.toJson<int?>(civId),
      'title': serializer.toJson<String>(title),
      'content': serializer.toJson<String>(content),
      'pinned': serializer.toJson<int>(pinned),
      'noteType': serializer.toJson<String>(noteType),
      'createdAt': serializer.toJson<String>(createdAt),
      'updatedAt': serializer.toJson<String>(updatedAt),
    };
  }

  NoteRow copyWith(
          {int? id,
          Value<int?> entityId = const Value.absent(),
          Value<int?> subjectId = const Value.absent(),
          Value<int?> turnId = const Value.absent(),
          Value<int?> civId = const Value.absent(),
          String? title,
          String? content,
          int? pinned,
          String? noteType,
          String? createdAt,
          String? updatedAt}) =>
      NoteRow(
        id: id ?? this.id,
        entityId: entityId.present ? entityId.value : this.entityId,
        subjectId: subjectId.present ? subjectId.value : this.subjectId,
        turnId: turnId.present ? turnId.value : this.turnId,
        civId: civId.present ? civId.value : this.civId,
        title: title ?? this.title,
        content: content ?? this.content,
        pinned: pinned ?? this.pinned,
        noteType: noteType ?? this.noteType,
        createdAt: createdAt ?? this.createdAt,
        updatedAt: updatedAt ?? this.updatedAt,
      );
  NoteRow copyWithCompanion(NotesCompanion data) {
    return NoteRow(
      id: data.id.present ? data.id.value : this.id,
      entityId: data.entityId.present ? data.entityId.value : this.entityId,
      subjectId: data.subjectId.present ? data.subjectId.value : this.subjectId,
      turnId: data.turnId.present ? data.turnId.value : this.turnId,
      civId: data.civId.present ? data.civId.value : this.civId,
      title: data.title.present ? data.title.value : this.title,
      content: data.content.present ? data.content.value : this.content,
      pinned: data.pinned.present ? data.pinned.value : this.pinned,
      noteType: data.noteType.present ? data.noteType.value : this.noteType,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('NoteRow(')
          ..write('id: $id, ')
          ..write('entityId: $entityId, ')
          ..write('subjectId: $subjectId, ')
          ..write('turnId: $turnId, ')
          ..write('civId: $civId, ')
          ..write('title: $title, ')
          ..write('content: $content, ')
          ..write('pinned: $pinned, ')
          ..write('noteType: $noteType, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, entityId, subjectId, turnId, civId, title,
      content, pinned, noteType, createdAt, updatedAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is NoteRow &&
          other.id == this.id &&
          other.entityId == this.entityId &&
          other.subjectId == this.subjectId &&
          other.turnId == this.turnId &&
          other.civId == this.civId &&
          other.title == this.title &&
          other.content == this.content &&
          other.pinned == this.pinned &&
          other.noteType == this.noteType &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt);
}

class NotesCompanion extends UpdateCompanion<NoteRow> {
  final Value<int> id;
  final Value<int?> entityId;
  final Value<int?> subjectId;
  final Value<int?> turnId;
  final Value<int?> civId;
  final Value<String> title;
  final Value<String> content;
  final Value<int> pinned;
  final Value<String> noteType;
  final Value<String> createdAt;
  final Value<String> updatedAt;
  const NotesCompanion({
    this.id = const Value.absent(),
    this.entityId = const Value.absent(),
    this.subjectId = const Value.absent(),
    this.turnId = const Value.absent(),
    this.civId = const Value.absent(),
    this.title = const Value.absent(),
    this.content = const Value.absent(),
    this.pinned = const Value.absent(),
    this.noteType = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
  });
  NotesCompanion.insert({
    this.id = const Value.absent(),
    this.entityId = const Value.absent(),
    this.subjectId = const Value.absent(),
    this.turnId = const Value.absent(),
    this.civId = const Value.absent(),
    this.title = const Value.absent(),
    this.content = const Value.absent(),
    this.pinned = const Value.absent(),
    this.noteType = const Value.absent(),
    required String createdAt,
    required String updatedAt,
  })  : createdAt = Value(createdAt),
        updatedAt = Value(updatedAt);
  static Insertable<NoteRow> custom({
    Expression<int>? id,
    Expression<int>? entityId,
    Expression<int>? subjectId,
    Expression<int>? turnId,
    Expression<int>? civId,
    Expression<String>? title,
    Expression<String>? content,
    Expression<int>? pinned,
    Expression<String>? noteType,
    Expression<String>? createdAt,
    Expression<String>? updatedAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (entityId != null) 'entity_id': entityId,
      if (subjectId != null) 'subject_id': subjectId,
      if (turnId != null) 'turn_id': turnId,
      if (civId != null) 'civ_id': civId,
      if (title != null) 'title': title,
      if (content != null) 'content': content,
      if (pinned != null) 'pinned': pinned,
      if (noteType != null) 'note_type': noteType,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
    });
  }

  NotesCompanion copyWith(
      {Value<int>? id,
      Value<int?>? entityId,
      Value<int?>? subjectId,
      Value<int?>? turnId,
      Value<int?>? civId,
      Value<String>? title,
      Value<String>? content,
      Value<int>? pinned,
      Value<String>? noteType,
      Value<String>? createdAt,
      Value<String>? updatedAt}) {
    return NotesCompanion(
      id: id ?? this.id,
      entityId: entityId ?? this.entityId,
      subjectId: subjectId ?? this.subjectId,
      turnId: turnId ?? this.turnId,
      civId: civId ?? this.civId,
      title: title ?? this.title,
      content: content ?? this.content,
      pinned: pinned ?? this.pinned,
      noteType: noteType ?? this.noteType,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (entityId.present) {
      map['entity_id'] = Variable<int>(entityId.value);
    }
    if (subjectId.present) {
      map['subject_id'] = Variable<int>(subjectId.value);
    }
    if (turnId.present) {
      map['turn_id'] = Variable<int>(turnId.value);
    }
    if (civId.present) {
      map['civ_id'] = Variable<int>(civId.value);
    }
    if (title.present) {
      map['title'] = Variable<String>(title.value);
    }
    if (content.present) {
      map['content'] = Variable<String>(content.value);
    }
    if (pinned.present) {
      map['pinned'] = Variable<int>(pinned.value);
    }
    if (noteType.present) {
      map['note_type'] = Variable<String>(noteType.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<String>(updatedAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('NotesCompanion(')
          ..write('id: $id, ')
          ..write('entityId: $entityId, ')
          ..write('subjectId: $subjectId, ')
          ..write('turnId: $turnId, ')
          ..write('civId: $civId, ')
          ..write('title: $title, ')
          ..write('content: $content, ')
          ..write('pinned: $pinned, ')
          ..write('noteType: $noteType, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }
}

class $MapMapsTable extends MapMaps with TableInfo<$MapMapsTable, MapRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $MapMapsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
      'id', aliasedName, false,
      hasAutoIncrement: true,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('PRIMARY KEY AUTOINCREMENT'));
  static const VerificationMeta _nameMeta = const VerificationMeta('name');
  @override
  late final GeneratedColumn<String> name = GeneratedColumn<String>(
      'name', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _imagePathMeta =
      const VerificationMeta('imagePath');
  @override
  late final GeneratedColumn<String> imagePath = GeneratedColumn<String>(
      'image_path', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _gridTypeMeta =
      const VerificationMeta('gridType');
  @override
  late final GeneratedColumn<String> gridType = GeneratedColumn<String>(
      'grid_type', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('hex'));
  static const VerificationMeta _gridColsMeta =
      const VerificationMeta('gridCols');
  @override
  late final GeneratedColumn<int> gridCols = GeneratedColumn<int>(
      'grid_cols', aliasedName, false,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultValue: const Constant(20));
  static const VerificationMeta _gridRowsMeta =
      const VerificationMeta('gridRows');
  @override
  late final GeneratedColumn<int> gridRows = GeneratedColumn<int>(
      'grid_rows', aliasedName, false,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultValue: const Constant(15));
  static const VerificationMeta _parentMapIdMeta =
      const VerificationMeta('parentMapId');
  @override
  late final GeneratedColumn<int> parentMapId = GeneratedColumn<int>(
      'parent_map_id', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _parentCellQMeta =
      const VerificationMeta('parentCellQ');
  @override
  late final GeneratedColumn<int> parentCellQ = GeneratedColumn<int>(
      'parent_cell_q', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _parentCellRMeta =
      const VerificationMeta('parentCellR');
  @override
  late final GeneratedColumn<int> parentCellR = GeneratedColumn<int>(
      'parent_cell_r', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _createdAtMeta =
      const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
      'created_at', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  @override
  List<GeneratedColumn> get $columns => [
        id,
        name,
        imagePath,
        gridType,
        gridCols,
        gridRows,
        parentMapId,
        parentCellQ,
        parentCellR,
        createdAt
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'map_maps';
  @override
  VerificationContext validateIntegrity(Insertable<MapRow> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('name')) {
      context.handle(
          _nameMeta, name.isAcceptableOrUnknown(data['name']!, _nameMeta));
    } else if (isInserting) {
      context.missing(_nameMeta);
    }
    if (data.containsKey('image_path')) {
      context.handle(_imagePathMeta,
          imagePath.isAcceptableOrUnknown(data['image_path']!, _imagePathMeta));
    }
    if (data.containsKey('grid_type')) {
      context.handle(_gridTypeMeta,
          gridType.isAcceptableOrUnknown(data['grid_type']!, _gridTypeMeta));
    }
    if (data.containsKey('grid_cols')) {
      context.handle(_gridColsMeta,
          gridCols.isAcceptableOrUnknown(data['grid_cols']!, _gridColsMeta));
    }
    if (data.containsKey('grid_rows')) {
      context.handle(_gridRowsMeta,
          gridRows.isAcceptableOrUnknown(data['grid_rows']!, _gridRowsMeta));
    }
    if (data.containsKey('parent_map_id')) {
      context.handle(
          _parentMapIdMeta,
          parentMapId.isAcceptableOrUnknown(
              data['parent_map_id']!, _parentMapIdMeta));
    }
    if (data.containsKey('parent_cell_q')) {
      context.handle(
          _parentCellQMeta,
          parentCellQ.isAcceptableOrUnknown(
              data['parent_cell_q']!, _parentCellQMeta));
    }
    if (data.containsKey('parent_cell_r')) {
      context.handle(
          _parentCellRMeta,
          parentCellR.isAcceptableOrUnknown(
              data['parent_cell_r']!, _parentCellRMeta));
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta,
          createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  MapRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return MapRow(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}id'])!,
      name: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}name'])!,
      imagePath: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}image_path']),
      gridType: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}grid_type'])!,
      gridCols: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}grid_cols'])!,
      gridRows: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}grid_rows'])!,
      parentMapId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}parent_map_id']),
      parentCellQ: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}parent_cell_q']),
      parentCellR: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}parent_cell_r']),
      createdAt: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}created_at'])!,
    );
  }

  @override
  $MapMapsTable createAlias(String alias) {
    return $MapMapsTable(attachedDatabase, alias);
  }
}

class MapRow extends DataClass implements Insertable<MapRow> {
  final int id;
  final String name;
  final String? imagePath;

  /// 'hex' (pointy-top) or 'square'
  final String gridType;
  final int gridCols;
  final int gridRows;

  /// Self-reference: this map drills into a cell of parent_map_id.
  /// Plain IntColumn — Drift doesn't support typed self-referencing FKs.
  final int? parentMapId;
  final int? parentCellQ;
  final int? parentCellR;
  final String createdAt;
  const MapRow(
      {required this.id,
      required this.name,
      this.imagePath,
      required this.gridType,
      required this.gridCols,
      required this.gridRows,
      this.parentMapId,
      this.parentCellQ,
      this.parentCellR,
      required this.createdAt});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['name'] = Variable<String>(name);
    if (!nullToAbsent || imagePath != null) {
      map['image_path'] = Variable<String>(imagePath);
    }
    map['grid_type'] = Variable<String>(gridType);
    map['grid_cols'] = Variable<int>(gridCols);
    map['grid_rows'] = Variable<int>(gridRows);
    if (!nullToAbsent || parentMapId != null) {
      map['parent_map_id'] = Variable<int>(parentMapId);
    }
    if (!nullToAbsent || parentCellQ != null) {
      map['parent_cell_q'] = Variable<int>(parentCellQ);
    }
    if (!nullToAbsent || parentCellR != null) {
      map['parent_cell_r'] = Variable<int>(parentCellR);
    }
    map['created_at'] = Variable<String>(createdAt);
    return map;
  }

  MapMapsCompanion toCompanion(bool nullToAbsent) {
    return MapMapsCompanion(
      id: Value(id),
      name: Value(name),
      imagePath: imagePath == null && nullToAbsent
          ? const Value.absent()
          : Value(imagePath),
      gridType: Value(gridType),
      gridCols: Value(gridCols),
      gridRows: Value(gridRows),
      parentMapId: parentMapId == null && nullToAbsent
          ? const Value.absent()
          : Value(parentMapId),
      parentCellQ: parentCellQ == null && nullToAbsent
          ? const Value.absent()
          : Value(parentCellQ),
      parentCellR: parentCellR == null && nullToAbsent
          ? const Value.absent()
          : Value(parentCellR),
      createdAt: Value(createdAt),
    );
  }

  factory MapRow.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return MapRow(
      id: serializer.fromJson<int>(json['id']),
      name: serializer.fromJson<String>(json['name']),
      imagePath: serializer.fromJson<String?>(json['imagePath']),
      gridType: serializer.fromJson<String>(json['gridType']),
      gridCols: serializer.fromJson<int>(json['gridCols']),
      gridRows: serializer.fromJson<int>(json['gridRows']),
      parentMapId: serializer.fromJson<int?>(json['parentMapId']),
      parentCellQ: serializer.fromJson<int?>(json['parentCellQ']),
      parentCellR: serializer.fromJson<int?>(json['parentCellR']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'name': serializer.toJson<String>(name),
      'imagePath': serializer.toJson<String?>(imagePath),
      'gridType': serializer.toJson<String>(gridType),
      'gridCols': serializer.toJson<int>(gridCols),
      'gridRows': serializer.toJson<int>(gridRows),
      'parentMapId': serializer.toJson<int?>(parentMapId),
      'parentCellQ': serializer.toJson<int?>(parentCellQ),
      'parentCellR': serializer.toJson<int?>(parentCellR),
      'createdAt': serializer.toJson<String>(createdAt),
    };
  }

  MapRow copyWith(
          {int? id,
          String? name,
          Value<String?> imagePath = const Value.absent(),
          String? gridType,
          int? gridCols,
          int? gridRows,
          Value<int?> parentMapId = const Value.absent(),
          Value<int?> parentCellQ = const Value.absent(),
          Value<int?> parentCellR = const Value.absent(),
          String? createdAt}) =>
      MapRow(
        id: id ?? this.id,
        name: name ?? this.name,
        imagePath: imagePath.present ? imagePath.value : this.imagePath,
        gridType: gridType ?? this.gridType,
        gridCols: gridCols ?? this.gridCols,
        gridRows: gridRows ?? this.gridRows,
        parentMapId: parentMapId.present ? parentMapId.value : this.parentMapId,
        parentCellQ: parentCellQ.present ? parentCellQ.value : this.parentCellQ,
        parentCellR: parentCellR.present ? parentCellR.value : this.parentCellR,
        createdAt: createdAt ?? this.createdAt,
      );
  MapRow copyWithCompanion(MapMapsCompanion data) {
    return MapRow(
      id: data.id.present ? data.id.value : this.id,
      name: data.name.present ? data.name.value : this.name,
      imagePath: data.imagePath.present ? data.imagePath.value : this.imagePath,
      gridType: data.gridType.present ? data.gridType.value : this.gridType,
      gridCols: data.gridCols.present ? data.gridCols.value : this.gridCols,
      gridRows: data.gridRows.present ? data.gridRows.value : this.gridRows,
      parentMapId:
          data.parentMapId.present ? data.parentMapId.value : this.parentMapId,
      parentCellQ:
          data.parentCellQ.present ? data.parentCellQ.value : this.parentCellQ,
      parentCellR:
          data.parentCellR.present ? data.parentCellR.value : this.parentCellR,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('MapRow(')
          ..write('id: $id, ')
          ..write('name: $name, ')
          ..write('imagePath: $imagePath, ')
          ..write('gridType: $gridType, ')
          ..write('gridCols: $gridCols, ')
          ..write('gridRows: $gridRows, ')
          ..write('parentMapId: $parentMapId, ')
          ..write('parentCellQ: $parentCellQ, ')
          ..write('parentCellR: $parentCellR, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, name, imagePath, gridType, gridCols,
      gridRows, parentMapId, parentCellQ, parentCellR, createdAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is MapRow &&
          other.id == this.id &&
          other.name == this.name &&
          other.imagePath == this.imagePath &&
          other.gridType == this.gridType &&
          other.gridCols == this.gridCols &&
          other.gridRows == this.gridRows &&
          other.parentMapId == this.parentMapId &&
          other.parentCellQ == this.parentCellQ &&
          other.parentCellR == this.parentCellR &&
          other.createdAt == this.createdAt);
}

class MapMapsCompanion extends UpdateCompanion<MapRow> {
  final Value<int> id;
  final Value<String> name;
  final Value<String?> imagePath;
  final Value<String> gridType;
  final Value<int> gridCols;
  final Value<int> gridRows;
  final Value<int?> parentMapId;
  final Value<int?> parentCellQ;
  final Value<int?> parentCellR;
  final Value<String> createdAt;
  const MapMapsCompanion({
    this.id = const Value.absent(),
    this.name = const Value.absent(),
    this.imagePath = const Value.absent(),
    this.gridType = const Value.absent(),
    this.gridCols = const Value.absent(),
    this.gridRows = const Value.absent(),
    this.parentMapId = const Value.absent(),
    this.parentCellQ = const Value.absent(),
    this.parentCellR = const Value.absent(),
    this.createdAt = const Value.absent(),
  });
  MapMapsCompanion.insert({
    this.id = const Value.absent(),
    required String name,
    this.imagePath = const Value.absent(),
    this.gridType = const Value.absent(),
    this.gridCols = const Value.absent(),
    this.gridRows = const Value.absent(),
    this.parentMapId = const Value.absent(),
    this.parentCellQ = const Value.absent(),
    this.parentCellR = const Value.absent(),
    required String createdAt,
  })  : name = Value(name),
        createdAt = Value(createdAt);
  static Insertable<MapRow> custom({
    Expression<int>? id,
    Expression<String>? name,
    Expression<String>? imagePath,
    Expression<String>? gridType,
    Expression<int>? gridCols,
    Expression<int>? gridRows,
    Expression<int>? parentMapId,
    Expression<int>? parentCellQ,
    Expression<int>? parentCellR,
    Expression<String>? createdAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (name != null) 'name': name,
      if (imagePath != null) 'image_path': imagePath,
      if (gridType != null) 'grid_type': gridType,
      if (gridCols != null) 'grid_cols': gridCols,
      if (gridRows != null) 'grid_rows': gridRows,
      if (parentMapId != null) 'parent_map_id': parentMapId,
      if (parentCellQ != null) 'parent_cell_q': parentCellQ,
      if (parentCellR != null) 'parent_cell_r': parentCellR,
      if (createdAt != null) 'created_at': createdAt,
    });
  }

  MapMapsCompanion copyWith(
      {Value<int>? id,
      Value<String>? name,
      Value<String?>? imagePath,
      Value<String>? gridType,
      Value<int>? gridCols,
      Value<int>? gridRows,
      Value<int?>? parentMapId,
      Value<int?>? parentCellQ,
      Value<int?>? parentCellR,
      Value<String>? createdAt}) {
    return MapMapsCompanion(
      id: id ?? this.id,
      name: name ?? this.name,
      imagePath: imagePath ?? this.imagePath,
      gridType: gridType ?? this.gridType,
      gridCols: gridCols ?? this.gridCols,
      gridRows: gridRows ?? this.gridRows,
      parentMapId: parentMapId ?? this.parentMapId,
      parentCellQ: parentCellQ ?? this.parentCellQ,
      parentCellR: parentCellR ?? this.parentCellR,
      createdAt: createdAt ?? this.createdAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (name.present) {
      map['name'] = Variable<String>(name.value);
    }
    if (imagePath.present) {
      map['image_path'] = Variable<String>(imagePath.value);
    }
    if (gridType.present) {
      map['grid_type'] = Variable<String>(gridType.value);
    }
    if (gridCols.present) {
      map['grid_cols'] = Variable<int>(gridCols.value);
    }
    if (gridRows.present) {
      map['grid_rows'] = Variable<int>(gridRows.value);
    }
    if (parentMapId.present) {
      map['parent_map_id'] = Variable<int>(parentMapId.value);
    }
    if (parentCellQ.present) {
      map['parent_cell_q'] = Variable<int>(parentCellQ.value);
    }
    if (parentCellR.present) {
      map['parent_cell_r'] = Variable<int>(parentCellR.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('MapMapsCompanion(')
          ..write('id: $id, ')
          ..write('name: $name, ')
          ..write('imagePath: $imagePath, ')
          ..write('gridType: $gridType, ')
          ..write('gridCols: $gridCols, ')
          ..write('gridRows: $gridRows, ')
          ..write('parentMapId: $parentMapId, ')
          ..write('parentCellQ: $parentCellQ, ')
          ..write('parentCellR: $parentCellR, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }
}

class $MapCellsTable extends MapCells
    with TableInfo<$MapCellsTable, MapCellRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $MapCellsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _mapIdMeta = const VerificationMeta('mapId');
  @override
  late final GeneratedColumn<int> mapId = GeneratedColumn<int>(
      'map_id', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _qMeta = const VerificationMeta('q');
  @override
  late final GeneratedColumn<int> q = GeneratedColumn<int>(
      'q', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _rMeta = const VerificationMeta('r');
  @override
  late final GeneratedColumn<int> r = GeneratedColumn<int>(
      'r', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _terrainTypeMeta =
      const VerificationMeta('terrainType');
  @override
  late final GeneratedColumn<String> terrainType = GeneratedColumn<String>(
      'terrain_type', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('plain'));
  static const VerificationMeta _controllingCivIdMeta =
      const VerificationMeta('controllingCivId');
  @override
  late final GeneratedColumn<int> controllingCivId = GeneratedColumn<int>(
      'controlling_civ_id', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _entityIdMeta =
      const VerificationMeta('entityId');
  @override
  late final GeneratedColumn<int> entityId = GeneratedColumn<int>(
      'entity_id', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _labelMeta = const VerificationMeta('label');
  @override
  late final GeneratedColumn<String> label = GeneratedColumn<String>(
      'label', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _childMapIdMeta =
      const VerificationMeta('childMapId');
  @override
  late final GeneratedColumn<int> childMapId = GeneratedColumn<int>(
      'child_map_id', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _metadataMeta =
      const VerificationMeta('metadata');
  @override
  late final GeneratedColumn<String> metadata = GeneratedColumn<String>(
      'metadata', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  @override
  List<GeneratedColumn> get $columns => [
        mapId,
        q,
        r,
        terrainType,
        controllingCivId,
        entityId,
        label,
        childMapId,
        metadata
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'map_cells';
  @override
  VerificationContext validateIntegrity(Insertable<MapCellRow> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('map_id')) {
      context.handle(
          _mapIdMeta, mapId.isAcceptableOrUnknown(data['map_id']!, _mapIdMeta));
    } else if (isInserting) {
      context.missing(_mapIdMeta);
    }
    if (data.containsKey('q')) {
      context.handle(_qMeta, q.isAcceptableOrUnknown(data['q']!, _qMeta));
    } else if (isInserting) {
      context.missing(_qMeta);
    }
    if (data.containsKey('r')) {
      context.handle(_rMeta, r.isAcceptableOrUnknown(data['r']!, _rMeta));
    } else if (isInserting) {
      context.missing(_rMeta);
    }
    if (data.containsKey('terrain_type')) {
      context.handle(
          _terrainTypeMeta,
          terrainType.isAcceptableOrUnknown(
              data['terrain_type']!, _terrainTypeMeta));
    }
    if (data.containsKey('controlling_civ_id')) {
      context.handle(
          _controllingCivIdMeta,
          controllingCivId.isAcceptableOrUnknown(
              data['controlling_civ_id']!, _controllingCivIdMeta));
    }
    if (data.containsKey('entity_id')) {
      context.handle(_entityIdMeta,
          entityId.isAcceptableOrUnknown(data['entity_id']!, _entityIdMeta));
    }
    if (data.containsKey('label')) {
      context.handle(
          _labelMeta, label.isAcceptableOrUnknown(data['label']!, _labelMeta));
    }
    if (data.containsKey('child_map_id')) {
      context.handle(
          _childMapIdMeta,
          childMapId.isAcceptableOrUnknown(
              data['child_map_id']!, _childMapIdMeta));
    }
    if (data.containsKey('metadata')) {
      context.handle(_metadataMeta,
          metadata.isAcceptableOrUnknown(data['metadata']!, _metadataMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {mapId, q, r};
  @override
  MapCellRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return MapCellRow(
      mapId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}map_id'])!,
      q: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}q'])!,
      r: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}r'])!,
      terrainType: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}terrain_type'])!,
      controllingCivId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}controlling_civ_id']),
      entityId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}entity_id']),
      label: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}label']),
      childMapId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}child_map_id']),
      metadata: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}metadata']),
    );
  }

  @override
  $MapCellsTable createAlias(String alias) {
    return $MapCellsTable(attachedDatabase, alias);
  }
}

class MapCellRow extends DataClass implements Insertable<MapCellRow> {
  final int mapId;
  final int q;
  final int r;

  /// plain|forest|mountain|river|coast|sea|desert|swamp|ruins
  final String terrainType;
  final int? controllingCivId;
  final int? entityId;
  final String? label;

  /// FK to a child map — clicking this cell drills into that map.
  final int? childMapId;

  /// JSON blob for arbitrary extra data.
  final String? metadata;
  const MapCellRow(
      {required this.mapId,
      required this.q,
      required this.r,
      required this.terrainType,
      this.controllingCivId,
      this.entityId,
      this.label,
      this.childMapId,
      this.metadata});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['map_id'] = Variable<int>(mapId);
    map['q'] = Variable<int>(q);
    map['r'] = Variable<int>(r);
    map['terrain_type'] = Variable<String>(terrainType);
    if (!nullToAbsent || controllingCivId != null) {
      map['controlling_civ_id'] = Variable<int>(controllingCivId);
    }
    if (!nullToAbsent || entityId != null) {
      map['entity_id'] = Variable<int>(entityId);
    }
    if (!nullToAbsent || label != null) {
      map['label'] = Variable<String>(label);
    }
    if (!nullToAbsent || childMapId != null) {
      map['child_map_id'] = Variable<int>(childMapId);
    }
    if (!nullToAbsent || metadata != null) {
      map['metadata'] = Variable<String>(metadata);
    }
    return map;
  }

  MapCellsCompanion toCompanion(bool nullToAbsent) {
    return MapCellsCompanion(
      mapId: Value(mapId),
      q: Value(q),
      r: Value(r),
      terrainType: Value(terrainType),
      controllingCivId: controllingCivId == null && nullToAbsent
          ? const Value.absent()
          : Value(controllingCivId),
      entityId: entityId == null && nullToAbsent
          ? const Value.absent()
          : Value(entityId),
      label:
          label == null && nullToAbsent ? const Value.absent() : Value(label),
      childMapId: childMapId == null && nullToAbsent
          ? const Value.absent()
          : Value(childMapId),
      metadata: metadata == null && nullToAbsent
          ? const Value.absent()
          : Value(metadata),
    );
  }

  factory MapCellRow.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return MapCellRow(
      mapId: serializer.fromJson<int>(json['mapId']),
      q: serializer.fromJson<int>(json['q']),
      r: serializer.fromJson<int>(json['r']),
      terrainType: serializer.fromJson<String>(json['terrainType']),
      controllingCivId: serializer.fromJson<int?>(json['controllingCivId']),
      entityId: serializer.fromJson<int?>(json['entityId']),
      label: serializer.fromJson<String?>(json['label']),
      childMapId: serializer.fromJson<int?>(json['childMapId']),
      metadata: serializer.fromJson<String?>(json['metadata']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'mapId': serializer.toJson<int>(mapId),
      'q': serializer.toJson<int>(q),
      'r': serializer.toJson<int>(r),
      'terrainType': serializer.toJson<String>(terrainType),
      'controllingCivId': serializer.toJson<int?>(controllingCivId),
      'entityId': serializer.toJson<int?>(entityId),
      'label': serializer.toJson<String?>(label),
      'childMapId': serializer.toJson<int?>(childMapId),
      'metadata': serializer.toJson<String?>(metadata),
    };
  }

  MapCellRow copyWith(
          {int? mapId,
          int? q,
          int? r,
          String? terrainType,
          Value<int?> controllingCivId = const Value.absent(),
          Value<int?> entityId = const Value.absent(),
          Value<String?> label = const Value.absent(),
          Value<int?> childMapId = const Value.absent(),
          Value<String?> metadata = const Value.absent()}) =>
      MapCellRow(
        mapId: mapId ?? this.mapId,
        q: q ?? this.q,
        r: r ?? this.r,
        terrainType: terrainType ?? this.terrainType,
        controllingCivId: controllingCivId.present
            ? controllingCivId.value
            : this.controllingCivId,
        entityId: entityId.present ? entityId.value : this.entityId,
        label: label.present ? label.value : this.label,
        childMapId: childMapId.present ? childMapId.value : this.childMapId,
        metadata: metadata.present ? metadata.value : this.metadata,
      );
  MapCellRow copyWithCompanion(MapCellsCompanion data) {
    return MapCellRow(
      mapId: data.mapId.present ? data.mapId.value : this.mapId,
      q: data.q.present ? data.q.value : this.q,
      r: data.r.present ? data.r.value : this.r,
      terrainType:
          data.terrainType.present ? data.terrainType.value : this.terrainType,
      controllingCivId: data.controllingCivId.present
          ? data.controllingCivId.value
          : this.controllingCivId,
      entityId: data.entityId.present ? data.entityId.value : this.entityId,
      label: data.label.present ? data.label.value : this.label,
      childMapId:
          data.childMapId.present ? data.childMapId.value : this.childMapId,
      metadata: data.metadata.present ? data.metadata.value : this.metadata,
    );
  }

  @override
  String toString() {
    return (StringBuffer('MapCellRow(')
          ..write('mapId: $mapId, ')
          ..write('q: $q, ')
          ..write('r: $r, ')
          ..write('terrainType: $terrainType, ')
          ..write('controllingCivId: $controllingCivId, ')
          ..write('entityId: $entityId, ')
          ..write('label: $label, ')
          ..write('childMapId: $childMapId, ')
          ..write('metadata: $metadata')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(mapId, q, r, terrainType, controllingCivId,
      entityId, label, childMapId, metadata);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is MapCellRow &&
          other.mapId == this.mapId &&
          other.q == this.q &&
          other.r == this.r &&
          other.terrainType == this.terrainType &&
          other.controllingCivId == this.controllingCivId &&
          other.entityId == this.entityId &&
          other.label == this.label &&
          other.childMapId == this.childMapId &&
          other.metadata == this.metadata);
}

class MapCellsCompanion extends UpdateCompanion<MapCellRow> {
  final Value<int> mapId;
  final Value<int> q;
  final Value<int> r;
  final Value<String> terrainType;
  final Value<int?> controllingCivId;
  final Value<int?> entityId;
  final Value<String?> label;
  final Value<int?> childMapId;
  final Value<String?> metadata;
  final Value<int> rowid;
  const MapCellsCompanion({
    this.mapId = const Value.absent(),
    this.q = const Value.absent(),
    this.r = const Value.absent(),
    this.terrainType = const Value.absent(),
    this.controllingCivId = const Value.absent(),
    this.entityId = const Value.absent(),
    this.label = const Value.absent(),
    this.childMapId = const Value.absent(),
    this.metadata = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  MapCellsCompanion.insert({
    required int mapId,
    required int q,
    required int r,
    this.terrainType = const Value.absent(),
    this.controllingCivId = const Value.absent(),
    this.entityId = const Value.absent(),
    this.label = const Value.absent(),
    this.childMapId = const Value.absent(),
    this.metadata = const Value.absent(),
    this.rowid = const Value.absent(),
  })  : mapId = Value(mapId),
        q = Value(q),
        r = Value(r);
  static Insertable<MapCellRow> custom({
    Expression<int>? mapId,
    Expression<int>? q,
    Expression<int>? r,
    Expression<String>? terrainType,
    Expression<int>? controllingCivId,
    Expression<int>? entityId,
    Expression<String>? label,
    Expression<int>? childMapId,
    Expression<String>? metadata,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (mapId != null) 'map_id': mapId,
      if (q != null) 'q': q,
      if (r != null) 'r': r,
      if (terrainType != null) 'terrain_type': terrainType,
      if (controllingCivId != null) 'controlling_civ_id': controllingCivId,
      if (entityId != null) 'entity_id': entityId,
      if (label != null) 'label': label,
      if (childMapId != null) 'child_map_id': childMapId,
      if (metadata != null) 'metadata': metadata,
      if (rowid != null) 'rowid': rowid,
    });
  }

  MapCellsCompanion copyWith(
      {Value<int>? mapId,
      Value<int>? q,
      Value<int>? r,
      Value<String>? terrainType,
      Value<int?>? controllingCivId,
      Value<int?>? entityId,
      Value<String?>? label,
      Value<int?>? childMapId,
      Value<String?>? metadata,
      Value<int>? rowid}) {
    return MapCellsCompanion(
      mapId: mapId ?? this.mapId,
      q: q ?? this.q,
      r: r ?? this.r,
      terrainType: terrainType ?? this.terrainType,
      controllingCivId: controllingCivId ?? this.controllingCivId,
      entityId: entityId ?? this.entityId,
      label: label ?? this.label,
      childMapId: childMapId ?? this.childMapId,
      metadata: metadata ?? this.metadata,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (mapId.present) {
      map['map_id'] = Variable<int>(mapId.value);
    }
    if (q.present) {
      map['q'] = Variable<int>(q.value);
    }
    if (r.present) {
      map['r'] = Variable<int>(r.value);
    }
    if (terrainType.present) {
      map['terrain_type'] = Variable<String>(terrainType.value);
    }
    if (controllingCivId.present) {
      map['controlling_civ_id'] = Variable<int>(controllingCivId.value);
    }
    if (entityId.present) {
      map['entity_id'] = Variable<int>(entityId.value);
    }
    if (label.present) {
      map['label'] = Variable<String>(label.value);
    }
    if (childMapId.present) {
      map['child_map_id'] = Variable<int>(childMapId.value);
    }
    if (metadata.present) {
      map['metadata'] = Variable<String>(metadata.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('MapCellsCompanion(')
          ..write('mapId: $mapId, ')
          ..write('q: $q, ')
          ..write('r: $r, ')
          ..write('terrainType: $terrainType, ')
          ..write('controllingCivId: $controllingCivId, ')
          ..write('entityId: $entityId, ')
          ..write('label: $label, ')
          ..write('childMapId: $childMapId, ')
          ..write('metadata: $metadata, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $MapCellEventsTable extends MapCellEvents
    with TableInfo<$MapCellEventsTable, MapCellEventRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $MapCellEventsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
      'id', aliasedName, false,
      hasAutoIncrement: true,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultConstraints:
          GeneratedColumn.constraintIsAlways('PRIMARY KEY AUTOINCREMENT'));
  static const VerificationMeta _mapIdMeta = const VerificationMeta('mapId');
  @override
  late final GeneratedColumn<int> mapId = GeneratedColumn<int>(
      'map_id', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _qMeta = const VerificationMeta('q');
  @override
  late final GeneratedColumn<int> q = GeneratedColumn<int>(
      'q', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _rMeta = const VerificationMeta('r');
  @override
  late final GeneratedColumn<int> r = GeneratedColumn<int>(
      'r', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _turnIdMeta = const VerificationMeta('turnId');
  @override
  late final GeneratedColumn<int> turnId = GeneratedColumn<int>(
      'turn_id', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _descriptionMeta =
      const VerificationMeta('description');
  @override
  late final GeneratedColumn<String> description = GeneratedColumn<String>(
      'description', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _eventTypeMeta =
      const VerificationMeta('eventType');
  @override
  late final GeneratedColumn<String> eventType = GeneratedColumn<String>(
      'event_type', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('note'));
  static const VerificationMeta _createdAtMeta =
      const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
      'created_at', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  @override
  List<GeneratedColumn> get $columns =>
      [id, mapId, q, r, turnId, description, eventType, createdAt];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'map_cell_events';
  @override
  VerificationContext validateIntegrity(Insertable<MapCellEventRow> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('map_id')) {
      context.handle(
          _mapIdMeta, mapId.isAcceptableOrUnknown(data['map_id']!, _mapIdMeta));
    } else if (isInserting) {
      context.missing(_mapIdMeta);
    }
    if (data.containsKey('q')) {
      context.handle(_qMeta, q.isAcceptableOrUnknown(data['q']!, _qMeta));
    } else if (isInserting) {
      context.missing(_qMeta);
    }
    if (data.containsKey('r')) {
      context.handle(_rMeta, r.isAcceptableOrUnknown(data['r']!, _rMeta));
    } else if (isInserting) {
      context.missing(_rMeta);
    }
    if (data.containsKey('turn_id')) {
      context.handle(_turnIdMeta,
          turnId.isAcceptableOrUnknown(data['turn_id']!, _turnIdMeta));
    }
    if (data.containsKey('description')) {
      context.handle(
          _descriptionMeta,
          description.isAcceptableOrUnknown(
              data['description']!, _descriptionMeta));
    } else if (isInserting) {
      context.missing(_descriptionMeta);
    }
    if (data.containsKey('event_type')) {
      context.handle(_eventTypeMeta,
          eventType.isAcceptableOrUnknown(data['event_type']!, _eventTypeMeta));
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta,
          createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  MapCellEventRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return MapCellEventRow(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}id'])!,
      mapId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}map_id'])!,
      q: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}q'])!,
      r: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}r'])!,
      turnId: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}turn_id']),
      description: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}description'])!,
      eventType: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}event_type'])!,
      createdAt: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}created_at'])!,
    );
  }

  @override
  $MapCellEventsTable createAlias(String alias) {
    return $MapCellEventsTable(attachedDatabase, alias);
  }
}

class MapCellEventRow extends DataClass implements Insertable<MapCellEventRow> {
  final int id;
  final int mapId;
  final int q;
  final int r;

  /// Optional FK to a game turn.
  final int? turnId;
  final String description;

  /// settlement|battle|discovery|diplomatic|note|migration|disaster
  final String eventType;
  final String createdAt;
  const MapCellEventRow(
      {required this.id,
      required this.mapId,
      required this.q,
      required this.r,
      this.turnId,
      required this.description,
      required this.eventType,
      required this.createdAt});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['map_id'] = Variable<int>(mapId);
    map['q'] = Variable<int>(q);
    map['r'] = Variable<int>(r);
    if (!nullToAbsent || turnId != null) {
      map['turn_id'] = Variable<int>(turnId);
    }
    map['description'] = Variable<String>(description);
    map['event_type'] = Variable<String>(eventType);
    map['created_at'] = Variable<String>(createdAt);
    return map;
  }

  MapCellEventsCompanion toCompanion(bool nullToAbsent) {
    return MapCellEventsCompanion(
      id: Value(id),
      mapId: Value(mapId),
      q: Value(q),
      r: Value(r),
      turnId:
          turnId == null && nullToAbsent ? const Value.absent() : Value(turnId),
      description: Value(description),
      eventType: Value(eventType),
      createdAt: Value(createdAt),
    );
  }

  factory MapCellEventRow.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return MapCellEventRow(
      id: serializer.fromJson<int>(json['id']),
      mapId: serializer.fromJson<int>(json['mapId']),
      q: serializer.fromJson<int>(json['q']),
      r: serializer.fromJson<int>(json['r']),
      turnId: serializer.fromJson<int?>(json['turnId']),
      description: serializer.fromJson<String>(json['description']),
      eventType: serializer.fromJson<String>(json['eventType']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'mapId': serializer.toJson<int>(mapId),
      'q': serializer.toJson<int>(q),
      'r': serializer.toJson<int>(r),
      'turnId': serializer.toJson<int?>(turnId),
      'description': serializer.toJson<String>(description),
      'eventType': serializer.toJson<String>(eventType),
      'createdAt': serializer.toJson<String>(createdAt),
    };
  }

  MapCellEventRow copyWith(
          {int? id,
          int? mapId,
          int? q,
          int? r,
          Value<int?> turnId = const Value.absent(),
          String? description,
          String? eventType,
          String? createdAt}) =>
      MapCellEventRow(
        id: id ?? this.id,
        mapId: mapId ?? this.mapId,
        q: q ?? this.q,
        r: r ?? this.r,
        turnId: turnId.present ? turnId.value : this.turnId,
        description: description ?? this.description,
        eventType: eventType ?? this.eventType,
        createdAt: createdAt ?? this.createdAt,
      );
  MapCellEventRow copyWithCompanion(MapCellEventsCompanion data) {
    return MapCellEventRow(
      id: data.id.present ? data.id.value : this.id,
      mapId: data.mapId.present ? data.mapId.value : this.mapId,
      q: data.q.present ? data.q.value : this.q,
      r: data.r.present ? data.r.value : this.r,
      turnId: data.turnId.present ? data.turnId.value : this.turnId,
      description:
          data.description.present ? data.description.value : this.description,
      eventType: data.eventType.present ? data.eventType.value : this.eventType,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('MapCellEventRow(')
          ..write('id: $id, ')
          ..write('mapId: $mapId, ')
          ..write('q: $q, ')
          ..write('r: $r, ')
          ..write('turnId: $turnId, ')
          ..write('description: $description, ')
          ..write('eventType: $eventType, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode =>
      Object.hash(id, mapId, q, r, turnId, description, eventType, createdAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is MapCellEventRow &&
          other.id == this.id &&
          other.mapId == this.mapId &&
          other.q == this.q &&
          other.r == this.r &&
          other.turnId == this.turnId &&
          other.description == this.description &&
          other.eventType == this.eventType &&
          other.createdAt == this.createdAt);
}

class MapCellEventsCompanion extends UpdateCompanion<MapCellEventRow> {
  final Value<int> id;
  final Value<int> mapId;
  final Value<int> q;
  final Value<int> r;
  final Value<int?> turnId;
  final Value<String> description;
  final Value<String> eventType;
  final Value<String> createdAt;
  const MapCellEventsCompanion({
    this.id = const Value.absent(),
    this.mapId = const Value.absent(),
    this.q = const Value.absent(),
    this.r = const Value.absent(),
    this.turnId = const Value.absent(),
    this.description = const Value.absent(),
    this.eventType = const Value.absent(),
    this.createdAt = const Value.absent(),
  });
  MapCellEventsCompanion.insert({
    this.id = const Value.absent(),
    required int mapId,
    required int q,
    required int r,
    this.turnId = const Value.absent(),
    required String description,
    this.eventType = const Value.absent(),
    required String createdAt,
  })  : mapId = Value(mapId),
        q = Value(q),
        r = Value(r),
        description = Value(description),
        createdAt = Value(createdAt);
  static Insertable<MapCellEventRow> custom({
    Expression<int>? id,
    Expression<int>? mapId,
    Expression<int>? q,
    Expression<int>? r,
    Expression<int>? turnId,
    Expression<String>? description,
    Expression<String>? eventType,
    Expression<String>? createdAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (mapId != null) 'map_id': mapId,
      if (q != null) 'q': q,
      if (r != null) 'r': r,
      if (turnId != null) 'turn_id': turnId,
      if (description != null) 'description': description,
      if (eventType != null) 'event_type': eventType,
      if (createdAt != null) 'created_at': createdAt,
    });
  }

  MapCellEventsCompanion copyWith(
      {Value<int>? id,
      Value<int>? mapId,
      Value<int>? q,
      Value<int>? r,
      Value<int?>? turnId,
      Value<String>? description,
      Value<String>? eventType,
      Value<String>? createdAt}) {
    return MapCellEventsCompanion(
      id: id ?? this.id,
      mapId: mapId ?? this.mapId,
      q: q ?? this.q,
      r: r ?? this.r,
      turnId: turnId ?? this.turnId,
      description: description ?? this.description,
      eventType: eventType ?? this.eventType,
      createdAt: createdAt ?? this.createdAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (mapId.present) {
      map['map_id'] = Variable<int>(mapId.value);
    }
    if (q.present) {
      map['q'] = Variable<int>(q.value);
    }
    if (r.present) {
      map['r'] = Variable<int>(r.value);
    }
    if (turnId.present) {
      map['turn_id'] = Variable<int>(turnId.value);
    }
    if (description.present) {
      map['description'] = Variable<String>(description.value);
    }
    if (eventType.present) {
      map['event_type'] = Variable<String>(eventType.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('MapCellEventsCompanion(')
          ..write('id: $id, ')
          ..write('mapId: $mapId, ')
          ..write('q: $q, ')
          ..write('r: $r, ')
          ..write('turnId: $turnId, ')
          ..write('description: $description, ')
          ..write('eventType: $eventType, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }
}

abstract class _$AurelmDatabase extends GeneratedDatabase {
  _$AurelmDatabase(QueryExecutor e) : super(e);
  $AurelmDatabaseManager get managers => $AurelmDatabaseManager(this);
  late final $CivCivilizationsTable civCivilizations =
      $CivCivilizationsTable(this);
  late final $TurnTurnsTable turnTurns = $TurnTurnsTable(this);
  late final $TurnSegmentsTable turnSegments = $TurnSegmentsTable(this);
  late final $EntityEntitiesTable entityEntities = $EntityEntitiesTable(this);
  late final $EntityAliasesTable entityAliases = $EntityAliasesTable(this);
  late final $EntityMentionsTable entityMentions = $EntityMentionsTable(this);
  late final $EntityRelationsTable entityRelations =
      $EntityRelationsTable(this);
  late final $PipelineRunsTable pipelineRuns = $PipelineRunsTable(this);
  late final $SubjectSubjectsTable subjectSubjects =
      $SubjectSubjectsTable(this);
  late final $SubjectOptionsTable subjectOptions = $SubjectOptionsTable(this);
  late final $SubjectResolutionsTable subjectResolutions =
      $SubjectResolutionsTable(this);
  late final $NotesTable notes = $NotesTable(this);
  late final $MapMapsTable mapMaps = $MapMapsTable(this);
  late final $MapCellsTable mapCells = $MapCellsTable(this);
  late final $MapCellEventsTable mapCellEvents = $MapCellEventsTable(this);
  late final CivilizationDao civilizationDao =
      CivilizationDao(this as AurelmDatabase);
  late final TurnDao turnDao = TurnDao(this as AurelmDatabase);
  late final EntityDao entityDao = EntityDao(this as AurelmDatabase);
  late final RelationDao relationDao = RelationDao(this as AurelmDatabase);
  late final PipelineDao pipelineDao = PipelineDao(this as AurelmDatabase);
  late final SubjectDao subjectDao = SubjectDao(this as AurelmDatabase);
  late final NotesDao notesDao = NotesDao(this as AurelmDatabase);
  late final MapDao mapDao = MapDao(this as AurelmDatabase);
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
        civCivilizations,
        turnTurns,
        turnSegments,
        entityEntities,
        entityAliases,
        entityMentions,
        entityRelations,
        pipelineRuns,
        subjectSubjects,
        subjectOptions,
        subjectResolutions,
        notes,
        mapMaps,
        mapCells,
        mapCellEvents
      ];
}

typedef $$CivCivilizationsTableCreateCompanionBuilder
    = CivCivilizationsCompanion Function({
  Value<int> id,
  required String name,
  Value<String?> playerName,
  Value<String?> discordChannelId,
  required String createdAt,
  required String updatedAt,
});
typedef $$CivCivilizationsTableUpdateCompanionBuilder
    = CivCivilizationsCompanion Function({
  Value<int> id,
  Value<String> name,
  Value<String?> playerName,
  Value<String?> discordChannelId,
  Value<String> createdAt,
  Value<String> updatedAt,
});

class $$CivCivilizationsTableFilterComposer
    extends Composer<_$AurelmDatabase, $CivCivilizationsTable> {
  $$CivCivilizationsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get name => $composableBuilder(
      column: $table.name, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get playerName => $composableBuilder(
      column: $table.playerName, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get discordChannelId => $composableBuilder(
      column: $table.discordChannelId,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get updatedAt => $composableBuilder(
      column: $table.updatedAt, builder: (column) => ColumnFilters(column));
}

class $$CivCivilizationsTableOrderingComposer
    extends Composer<_$AurelmDatabase, $CivCivilizationsTable> {
  $$CivCivilizationsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get name => $composableBuilder(
      column: $table.name, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get playerName => $composableBuilder(
      column: $table.playerName, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get discordChannelId => $composableBuilder(
      column: $table.discordChannelId,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get updatedAt => $composableBuilder(
      column: $table.updatedAt, builder: (column) => ColumnOrderings(column));
}

class $$CivCivilizationsTableAnnotationComposer
    extends Composer<_$AurelmDatabase, $CivCivilizationsTable> {
  $$CivCivilizationsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get name =>
      $composableBuilder(column: $table.name, builder: (column) => column);

  GeneratedColumn<String> get playerName => $composableBuilder(
      column: $table.playerName, builder: (column) => column);

  GeneratedColumn<String> get discordChannelId => $composableBuilder(
      column: $table.discordChannelId, builder: (column) => column);

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  GeneratedColumn<String> get updatedAt =>
      $composableBuilder(column: $table.updatedAt, builder: (column) => column);
}

class $$CivCivilizationsTableTableManager extends RootTableManager<
    _$AurelmDatabase,
    $CivCivilizationsTable,
    CivRow,
    $$CivCivilizationsTableFilterComposer,
    $$CivCivilizationsTableOrderingComposer,
    $$CivCivilizationsTableAnnotationComposer,
    $$CivCivilizationsTableCreateCompanionBuilder,
    $$CivCivilizationsTableUpdateCompanionBuilder,
    (CivRow, BaseReferences<_$AurelmDatabase, $CivCivilizationsTable, CivRow>),
    CivRow,
    PrefetchHooks Function()> {
  $$CivCivilizationsTableTableManager(
      _$AurelmDatabase db, $CivCivilizationsTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$CivCivilizationsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$CivCivilizationsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$CivCivilizationsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<int> id = const Value.absent(),
            Value<String> name = const Value.absent(),
            Value<String?> playerName = const Value.absent(),
            Value<String?> discordChannelId = const Value.absent(),
            Value<String> createdAt = const Value.absent(),
            Value<String> updatedAt = const Value.absent(),
          }) =>
              CivCivilizationsCompanion(
            id: id,
            name: name,
            playerName: playerName,
            discordChannelId: discordChannelId,
            createdAt: createdAt,
            updatedAt: updatedAt,
          ),
          createCompanionCallback: ({
            Value<int> id = const Value.absent(),
            required String name,
            Value<String?> playerName = const Value.absent(),
            Value<String?> discordChannelId = const Value.absent(),
            required String createdAt,
            required String updatedAt,
          }) =>
              CivCivilizationsCompanion.insert(
            id: id,
            name: name,
            playerName: playerName,
            discordChannelId: discordChannelId,
            createdAt: createdAt,
            updatedAt: updatedAt,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$CivCivilizationsTableProcessedTableManager = ProcessedTableManager<
    _$AurelmDatabase,
    $CivCivilizationsTable,
    CivRow,
    $$CivCivilizationsTableFilterComposer,
    $$CivCivilizationsTableOrderingComposer,
    $$CivCivilizationsTableAnnotationComposer,
    $$CivCivilizationsTableCreateCompanionBuilder,
    $$CivCivilizationsTableUpdateCompanionBuilder,
    (CivRow, BaseReferences<_$AurelmDatabase, $CivCivilizationsTable, CivRow>),
    CivRow,
    PrefetchHooks Function()>;
typedef $$TurnTurnsTableCreateCompanionBuilder = TurnTurnsCompanion Function({
  Value<int> id,
  required int civId,
  required int turnNumber,
  Value<String?> title,
  Value<String?> summary,
  Value<String?> detailedSummary,
  required String rawMessageIds,
  Value<String> turnType,
  Value<String?> gameDateStart,
  Value<String?> gameDateEnd,
  required String createdAt,
  Value<String?> processedAt,
  Value<String?> thematicTags,
  Value<String?> technologies,
  Value<String?> resources,
  Value<String?> beliefs,
  Value<String?> geography,
  Value<String?> keyEvents,
  Value<String?> choicesMade,
  Value<String?> choicesProposed,
  Value<String?> techEra,
  Value<String?> fantasyLevel,
  Value<String?> noveltySummary,
  Value<String?> newEntityIds,
  Value<String?> playerStrategy,
  Value<String?> strategyTags,
});
typedef $$TurnTurnsTableUpdateCompanionBuilder = TurnTurnsCompanion Function({
  Value<int> id,
  Value<int> civId,
  Value<int> turnNumber,
  Value<String?> title,
  Value<String?> summary,
  Value<String?> detailedSummary,
  Value<String> rawMessageIds,
  Value<String> turnType,
  Value<String?> gameDateStart,
  Value<String?> gameDateEnd,
  Value<String> createdAt,
  Value<String?> processedAt,
  Value<String?> thematicTags,
  Value<String?> technologies,
  Value<String?> resources,
  Value<String?> beliefs,
  Value<String?> geography,
  Value<String?> keyEvents,
  Value<String?> choicesMade,
  Value<String?> choicesProposed,
  Value<String?> techEra,
  Value<String?> fantasyLevel,
  Value<String?> noveltySummary,
  Value<String?> newEntityIds,
  Value<String?> playerStrategy,
  Value<String?> strategyTags,
});

class $$TurnTurnsTableFilterComposer
    extends Composer<_$AurelmDatabase, $TurnTurnsTable> {
  $$TurnTurnsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get civId => $composableBuilder(
      column: $table.civId, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get turnNumber => $composableBuilder(
      column: $table.turnNumber, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get title => $composableBuilder(
      column: $table.title, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get summary => $composableBuilder(
      column: $table.summary, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get detailedSummary => $composableBuilder(
      column: $table.detailedSummary,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get rawMessageIds => $composableBuilder(
      column: $table.rawMessageIds, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get turnType => $composableBuilder(
      column: $table.turnType, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get gameDateStart => $composableBuilder(
      column: $table.gameDateStart, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get gameDateEnd => $composableBuilder(
      column: $table.gameDateEnd, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get processedAt => $composableBuilder(
      column: $table.processedAt, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get thematicTags => $composableBuilder(
      column: $table.thematicTags, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get technologies => $composableBuilder(
      column: $table.technologies, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get resources => $composableBuilder(
      column: $table.resources, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get beliefs => $composableBuilder(
      column: $table.beliefs, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get geography => $composableBuilder(
      column: $table.geography, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get keyEvents => $composableBuilder(
      column: $table.keyEvents, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get choicesMade => $composableBuilder(
      column: $table.choicesMade, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get choicesProposed => $composableBuilder(
      column: $table.choicesProposed,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get techEra => $composableBuilder(
      column: $table.techEra, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get fantasyLevel => $composableBuilder(
      column: $table.fantasyLevel, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get noveltySummary => $composableBuilder(
      column: $table.noveltySummary,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get newEntityIds => $composableBuilder(
      column: $table.newEntityIds, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get playerStrategy => $composableBuilder(
      column: $table.playerStrategy,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get strategyTags => $composableBuilder(
      column: $table.strategyTags, builder: (column) => ColumnFilters(column));
}

class $$TurnTurnsTableOrderingComposer
    extends Composer<_$AurelmDatabase, $TurnTurnsTable> {
  $$TurnTurnsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get civId => $composableBuilder(
      column: $table.civId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get turnNumber => $composableBuilder(
      column: $table.turnNumber, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get title => $composableBuilder(
      column: $table.title, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get summary => $composableBuilder(
      column: $table.summary, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get detailedSummary => $composableBuilder(
      column: $table.detailedSummary,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get rawMessageIds => $composableBuilder(
      column: $table.rawMessageIds,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get turnType => $composableBuilder(
      column: $table.turnType, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get gameDateStart => $composableBuilder(
      column: $table.gameDateStart,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get gameDateEnd => $composableBuilder(
      column: $table.gameDateEnd, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get processedAt => $composableBuilder(
      column: $table.processedAt, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get thematicTags => $composableBuilder(
      column: $table.thematicTags,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get technologies => $composableBuilder(
      column: $table.technologies,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get resources => $composableBuilder(
      column: $table.resources, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get beliefs => $composableBuilder(
      column: $table.beliefs, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get geography => $composableBuilder(
      column: $table.geography, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get keyEvents => $composableBuilder(
      column: $table.keyEvents, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get choicesMade => $composableBuilder(
      column: $table.choicesMade, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get choicesProposed => $composableBuilder(
      column: $table.choicesProposed,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get techEra => $composableBuilder(
      column: $table.techEra, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get fantasyLevel => $composableBuilder(
      column: $table.fantasyLevel,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get noveltySummary => $composableBuilder(
      column: $table.noveltySummary,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get newEntityIds => $composableBuilder(
      column: $table.newEntityIds,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get playerStrategy => $composableBuilder(
      column: $table.playerStrategy,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get strategyTags => $composableBuilder(
      column: $table.strategyTags,
      builder: (column) => ColumnOrderings(column));
}

class $$TurnTurnsTableAnnotationComposer
    extends Composer<_$AurelmDatabase, $TurnTurnsTable> {
  $$TurnTurnsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get civId =>
      $composableBuilder(column: $table.civId, builder: (column) => column);

  GeneratedColumn<int> get turnNumber => $composableBuilder(
      column: $table.turnNumber, builder: (column) => column);

  GeneratedColumn<String> get title =>
      $composableBuilder(column: $table.title, builder: (column) => column);

  GeneratedColumn<String> get summary =>
      $composableBuilder(column: $table.summary, builder: (column) => column);

  GeneratedColumn<String> get detailedSummary => $composableBuilder(
      column: $table.detailedSummary, builder: (column) => column);

  GeneratedColumn<String> get rawMessageIds => $composableBuilder(
      column: $table.rawMessageIds, builder: (column) => column);

  GeneratedColumn<String> get turnType =>
      $composableBuilder(column: $table.turnType, builder: (column) => column);

  GeneratedColumn<String> get gameDateStart => $composableBuilder(
      column: $table.gameDateStart, builder: (column) => column);

  GeneratedColumn<String> get gameDateEnd => $composableBuilder(
      column: $table.gameDateEnd, builder: (column) => column);

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  GeneratedColumn<String> get processedAt => $composableBuilder(
      column: $table.processedAt, builder: (column) => column);

  GeneratedColumn<String> get thematicTags => $composableBuilder(
      column: $table.thematicTags, builder: (column) => column);

  GeneratedColumn<String> get technologies => $composableBuilder(
      column: $table.technologies, builder: (column) => column);

  GeneratedColumn<String> get resources =>
      $composableBuilder(column: $table.resources, builder: (column) => column);

  GeneratedColumn<String> get beliefs =>
      $composableBuilder(column: $table.beliefs, builder: (column) => column);

  GeneratedColumn<String> get geography =>
      $composableBuilder(column: $table.geography, builder: (column) => column);

  GeneratedColumn<String> get keyEvents =>
      $composableBuilder(column: $table.keyEvents, builder: (column) => column);

  GeneratedColumn<String> get choicesMade => $composableBuilder(
      column: $table.choicesMade, builder: (column) => column);

  GeneratedColumn<String> get choicesProposed => $composableBuilder(
      column: $table.choicesProposed, builder: (column) => column);

  GeneratedColumn<String> get techEra =>
      $composableBuilder(column: $table.techEra, builder: (column) => column);

  GeneratedColumn<String> get fantasyLevel => $composableBuilder(
      column: $table.fantasyLevel, builder: (column) => column);

  GeneratedColumn<String> get noveltySummary => $composableBuilder(
      column: $table.noveltySummary, builder: (column) => column);

  GeneratedColumn<String> get newEntityIds => $composableBuilder(
      column: $table.newEntityIds, builder: (column) => column);

  GeneratedColumn<String> get playerStrategy => $composableBuilder(
      column: $table.playerStrategy, builder: (column) => column);

  GeneratedColumn<String> get strategyTags => $composableBuilder(
      column: $table.strategyTags, builder: (column) => column);
}

class $$TurnTurnsTableTableManager extends RootTableManager<
    _$AurelmDatabase,
    $TurnTurnsTable,
    TurnRow,
    $$TurnTurnsTableFilterComposer,
    $$TurnTurnsTableOrderingComposer,
    $$TurnTurnsTableAnnotationComposer,
    $$TurnTurnsTableCreateCompanionBuilder,
    $$TurnTurnsTableUpdateCompanionBuilder,
    (TurnRow, BaseReferences<_$AurelmDatabase, $TurnTurnsTable, TurnRow>),
    TurnRow,
    PrefetchHooks Function()> {
  $$TurnTurnsTableTableManager(_$AurelmDatabase db, $TurnTurnsTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$TurnTurnsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$TurnTurnsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$TurnTurnsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<int> id = const Value.absent(),
            Value<int> civId = const Value.absent(),
            Value<int> turnNumber = const Value.absent(),
            Value<String?> title = const Value.absent(),
            Value<String?> summary = const Value.absent(),
            Value<String?> detailedSummary = const Value.absent(),
            Value<String> rawMessageIds = const Value.absent(),
            Value<String> turnType = const Value.absent(),
            Value<String?> gameDateStart = const Value.absent(),
            Value<String?> gameDateEnd = const Value.absent(),
            Value<String> createdAt = const Value.absent(),
            Value<String?> processedAt = const Value.absent(),
            Value<String?> thematicTags = const Value.absent(),
            Value<String?> technologies = const Value.absent(),
            Value<String?> resources = const Value.absent(),
            Value<String?> beliefs = const Value.absent(),
            Value<String?> geography = const Value.absent(),
            Value<String?> keyEvents = const Value.absent(),
            Value<String?> choicesMade = const Value.absent(),
            Value<String?> choicesProposed = const Value.absent(),
            Value<String?> techEra = const Value.absent(),
            Value<String?> fantasyLevel = const Value.absent(),
            Value<String?> noveltySummary = const Value.absent(),
            Value<String?> newEntityIds = const Value.absent(),
            Value<String?> playerStrategy = const Value.absent(),
            Value<String?> strategyTags = const Value.absent(),
          }) =>
              TurnTurnsCompanion(
            id: id,
            civId: civId,
            turnNumber: turnNumber,
            title: title,
            summary: summary,
            detailedSummary: detailedSummary,
            rawMessageIds: rawMessageIds,
            turnType: turnType,
            gameDateStart: gameDateStart,
            gameDateEnd: gameDateEnd,
            createdAt: createdAt,
            processedAt: processedAt,
            thematicTags: thematicTags,
            technologies: technologies,
            resources: resources,
            beliefs: beliefs,
            geography: geography,
            keyEvents: keyEvents,
            choicesMade: choicesMade,
            choicesProposed: choicesProposed,
            techEra: techEra,
            fantasyLevel: fantasyLevel,
            noveltySummary: noveltySummary,
            newEntityIds: newEntityIds,
            playerStrategy: playerStrategy,
            strategyTags: strategyTags,
          ),
          createCompanionCallback: ({
            Value<int> id = const Value.absent(),
            required int civId,
            required int turnNumber,
            Value<String?> title = const Value.absent(),
            Value<String?> summary = const Value.absent(),
            Value<String?> detailedSummary = const Value.absent(),
            required String rawMessageIds,
            Value<String> turnType = const Value.absent(),
            Value<String?> gameDateStart = const Value.absent(),
            Value<String?> gameDateEnd = const Value.absent(),
            required String createdAt,
            Value<String?> processedAt = const Value.absent(),
            Value<String?> thematicTags = const Value.absent(),
            Value<String?> technologies = const Value.absent(),
            Value<String?> resources = const Value.absent(),
            Value<String?> beliefs = const Value.absent(),
            Value<String?> geography = const Value.absent(),
            Value<String?> keyEvents = const Value.absent(),
            Value<String?> choicesMade = const Value.absent(),
            Value<String?> choicesProposed = const Value.absent(),
            Value<String?> techEra = const Value.absent(),
            Value<String?> fantasyLevel = const Value.absent(),
            Value<String?> noveltySummary = const Value.absent(),
            Value<String?> newEntityIds = const Value.absent(),
            Value<String?> playerStrategy = const Value.absent(),
            Value<String?> strategyTags = const Value.absent(),
          }) =>
              TurnTurnsCompanion.insert(
            id: id,
            civId: civId,
            turnNumber: turnNumber,
            title: title,
            summary: summary,
            detailedSummary: detailedSummary,
            rawMessageIds: rawMessageIds,
            turnType: turnType,
            gameDateStart: gameDateStart,
            gameDateEnd: gameDateEnd,
            createdAt: createdAt,
            processedAt: processedAt,
            thematicTags: thematicTags,
            technologies: technologies,
            resources: resources,
            beliefs: beliefs,
            geography: geography,
            keyEvents: keyEvents,
            choicesMade: choicesMade,
            choicesProposed: choicesProposed,
            techEra: techEra,
            fantasyLevel: fantasyLevel,
            noveltySummary: noveltySummary,
            newEntityIds: newEntityIds,
            playerStrategy: playerStrategy,
            strategyTags: strategyTags,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$TurnTurnsTableProcessedTableManager = ProcessedTableManager<
    _$AurelmDatabase,
    $TurnTurnsTable,
    TurnRow,
    $$TurnTurnsTableFilterComposer,
    $$TurnTurnsTableOrderingComposer,
    $$TurnTurnsTableAnnotationComposer,
    $$TurnTurnsTableCreateCompanionBuilder,
    $$TurnTurnsTableUpdateCompanionBuilder,
    (TurnRow, BaseReferences<_$AurelmDatabase, $TurnTurnsTable, TurnRow>),
    TurnRow,
    PrefetchHooks Function()>;
typedef $$TurnSegmentsTableCreateCompanionBuilder = TurnSegmentsCompanion
    Function({
  Value<int> id,
  required int turnId,
  required int segmentOrder,
  required String segmentType,
  required String content,
  Value<String> source,
});
typedef $$TurnSegmentsTableUpdateCompanionBuilder = TurnSegmentsCompanion
    Function({
  Value<int> id,
  Value<int> turnId,
  Value<int> segmentOrder,
  Value<String> segmentType,
  Value<String> content,
  Value<String> source,
});

class $$TurnSegmentsTableFilterComposer
    extends Composer<_$AurelmDatabase, $TurnSegmentsTable> {
  $$TurnSegmentsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get turnId => $composableBuilder(
      column: $table.turnId, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get segmentOrder => $composableBuilder(
      column: $table.segmentOrder, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get segmentType => $composableBuilder(
      column: $table.segmentType, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get content => $composableBuilder(
      column: $table.content, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get source => $composableBuilder(
      column: $table.source, builder: (column) => ColumnFilters(column));
}

class $$TurnSegmentsTableOrderingComposer
    extends Composer<_$AurelmDatabase, $TurnSegmentsTable> {
  $$TurnSegmentsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get turnId => $composableBuilder(
      column: $table.turnId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get segmentOrder => $composableBuilder(
      column: $table.segmentOrder,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get segmentType => $composableBuilder(
      column: $table.segmentType, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get content => $composableBuilder(
      column: $table.content, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get source => $composableBuilder(
      column: $table.source, builder: (column) => ColumnOrderings(column));
}

class $$TurnSegmentsTableAnnotationComposer
    extends Composer<_$AurelmDatabase, $TurnSegmentsTable> {
  $$TurnSegmentsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get turnId =>
      $composableBuilder(column: $table.turnId, builder: (column) => column);

  GeneratedColumn<int> get segmentOrder => $composableBuilder(
      column: $table.segmentOrder, builder: (column) => column);

  GeneratedColumn<String> get segmentType => $composableBuilder(
      column: $table.segmentType, builder: (column) => column);

  GeneratedColumn<String> get content =>
      $composableBuilder(column: $table.content, builder: (column) => column);

  GeneratedColumn<String> get source =>
      $composableBuilder(column: $table.source, builder: (column) => column);
}

class $$TurnSegmentsTableTableManager extends RootTableManager<
    _$AurelmDatabase,
    $TurnSegmentsTable,
    SegmentRow,
    $$TurnSegmentsTableFilterComposer,
    $$TurnSegmentsTableOrderingComposer,
    $$TurnSegmentsTableAnnotationComposer,
    $$TurnSegmentsTableCreateCompanionBuilder,
    $$TurnSegmentsTableUpdateCompanionBuilder,
    (
      SegmentRow,
      BaseReferences<_$AurelmDatabase, $TurnSegmentsTable, SegmentRow>
    ),
    SegmentRow,
    PrefetchHooks Function()> {
  $$TurnSegmentsTableTableManager(_$AurelmDatabase db, $TurnSegmentsTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$TurnSegmentsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$TurnSegmentsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$TurnSegmentsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<int> id = const Value.absent(),
            Value<int> turnId = const Value.absent(),
            Value<int> segmentOrder = const Value.absent(),
            Value<String> segmentType = const Value.absent(),
            Value<String> content = const Value.absent(),
            Value<String> source = const Value.absent(),
          }) =>
              TurnSegmentsCompanion(
            id: id,
            turnId: turnId,
            segmentOrder: segmentOrder,
            segmentType: segmentType,
            content: content,
            source: source,
          ),
          createCompanionCallback: ({
            Value<int> id = const Value.absent(),
            required int turnId,
            required int segmentOrder,
            required String segmentType,
            required String content,
            Value<String> source = const Value.absent(),
          }) =>
              TurnSegmentsCompanion.insert(
            id: id,
            turnId: turnId,
            segmentOrder: segmentOrder,
            segmentType: segmentType,
            content: content,
            source: source,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$TurnSegmentsTableProcessedTableManager = ProcessedTableManager<
    _$AurelmDatabase,
    $TurnSegmentsTable,
    SegmentRow,
    $$TurnSegmentsTableFilterComposer,
    $$TurnSegmentsTableOrderingComposer,
    $$TurnSegmentsTableAnnotationComposer,
    $$TurnSegmentsTableCreateCompanionBuilder,
    $$TurnSegmentsTableUpdateCompanionBuilder,
    (
      SegmentRow,
      BaseReferences<_$AurelmDatabase, $TurnSegmentsTable, SegmentRow>
    ),
    SegmentRow,
    PrefetchHooks Function()>;
typedef $$EntityEntitiesTableCreateCompanionBuilder = EntityEntitiesCompanion
    Function({
  Value<int> id,
  required String canonicalName,
  required String entityType,
  Value<int?> civId,
  Value<String?> description,
  Value<int?> firstSeenTurn,
  Value<int?> lastSeenTurn,
  Value<int> isActive,
  required String createdAt,
  required String updatedAt,
  Value<bool> hidden,
  Value<bool> disabled,
  Value<String?> disabledAt,
  Value<String?> tags,
});
typedef $$EntityEntitiesTableUpdateCompanionBuilder = EntityEntitiesCompanion
    Function({
  Value<int> id,
  Value<String> canonicalName,
  Value<String> entityType,
  Value<int?> civId,
  Value<String?> description,
  Value<int?> firstSeenTurn,
  Value<int?> lastSeenTurn,
  Value<int> isActive,
  Value<String> createdAt,
  Value<String> updatedAt,
  Value<bool> hidden,
  Value<bool> disabled,
  Value<String?> disabledAt,
  Value<String?> tags,
});

class $$EntityEntitiesTableFilterComposer
    extends Composer<_$AurelmDatabase, $EntityEntitiesTable> {
  $$EntityEntitiesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get canonicalName => $composableBuilder(
      column: $table.canonicalName, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get entityType => $composableBuilder(
      column: $table.entityType, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get civId => $composableBuilder(
      column: $table.civId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get firstSeenTurn => $composableBuilder(
      column: $table.firstSeenTurn, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get lastSeenTurn => $composableBuilder(
      column: $table.lastSeenTurn, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get isActive => $composableBuilder(
      column: $table.isActive, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get updatedAt => $composableBuilder(
      column: $table.updatedAt, builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get hidden => $composableBuilder(
      column: $table.hidden, builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get disabled => $composableBuilder(
      column: $table.disabled, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get disabledAt => $composableBuilder(
      column: $table.disabledAt, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get tags => $composableBuilder(
      column: $table.tags, builder: (column) => ColumnFilters(column));
}

class $$EntityEntitiesTableOrderingComposer
    extends Composer<_$AurelmDatabase, $EntityEntitiesTable> {
  $$EntityEntitiesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get canonicalName => $composableBuilder(
      column: $table.canonicalName,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get entityType => $composableBuilder(
      column: $table.entityType, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get civId => $composableBuilder(
      column: $table.civId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get firstSeenTurn => $composableBuilder(
      column: $table.firstSeenTurn,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get lastSeenTurn => $composableBuilder(
      column: $table.lastSeenTurn,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get isActive => $composableBuilder(
      column: $table.isActive, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get updatedAt => $composableBuilder(
      column: $table.updatedAt, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get hidden => $composableBuilder(
      column: $table.hidden, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get disabled => $composableBuilder(
      column: $table.disabled, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get disabledAt => $composableBuilder(
      column: $table.disabledAt, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get tags => $composableBuilder(
      column: $table.tags, builder: (column) => ColumnOrderings(column));
}

class $$EntityEntitiesTableAnnotationComposer
    extends Composer<_$AurelmDatabase, $EntityEntitiesTable> {
  $$EntityEntitiesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get canonicalName => $composableBuilder(
      column: $table.canonicalName, builder: (column) => column);

  GeneratedColumn<String> get entityType => $composableBuilder(
      column: $table.entityType, builder: (column) => column);

  GeneratedColumn<int> get civId =>
      $composableBuilder(column: $table.civId, builder: (column) => column);

  GeneratedColumn<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => column);

  GeneratedColumn<int> get firstSeenTurn => $composableBuilder(
      column: $table.firstSeenTurn, builder: (column) => column);

  GeneratedColumn<int> get lastSeenTurn => $composableBuilder(
      column: $table.lastSeenTurn, builder: (column) => column);

  GeneratedColumn<int> get isActive =>
      $composableBuilder(column: $table.isActive, builder: (column) => column);

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  GeneratedColumn<String> get updatedAt =>
      $composableBuilder(column: $table.updatedAt, builder: (column) => column);

  GeneratedColumn<bool> get hidden =>
      $composableBuilder(column: $table.hidden, builder: (column) => column);

  GeneratedColumn<bool> get disabled =>
      $composableBuilder(column: $table.disabled, builder: (column) => column);

  GeneratedColumn<String> get disabledAt => $composableBuilder(
      column: $table.disabledAt, builder: (column) => column);

  GeneratedColumn<String> get tags =>
      $composableBuilder(column: $table.tags, builder: (column) => column);
}

class $$EntityEntitiesTableTableManager extends RootTableManager<
    _$AurelmDatabase,
    $EntityEntitiesTable,
    EntityRow,
    $$EntityEntitiesTableFilterComposer,
    $$EntityEntitiesTableOrderingComposer,
    $$EntityEntitiesTableAnnotationComposer,
    $$EntityEntitiesTableCreateCompanionBuilder,
    $$EntityEntitiesTableUpdateCompanionBuilder,
    (
      EntityRow,
      BaseReferences<_$AurelmDatabase, $EntityEntitiesTable, EntityRow>
    ),
    EntityRow,
    PrefetchHooks Function()> {
  $$EntityEntitiesTableTableManager(
      _$AurelmDatabase db, $EntityEntitiesTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$EntityEntitiesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$EntityEntitiesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$EntityEntitiesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<int> id = const Value.absent(),
            Value<String> canonicalName = const Value.absent(),
            Value<String> entityType = const Value.absent(),
            Value<int?> civId = const Value.absent(),
            Value<String?> description = const Value.absent(),
            Value<int?> firstSeenTurn = const Value.absent(),
            Value<int?> lastSeenTurn = const Value.absent(),
            Value<int> isActive = const Value.absent(),
            Value<String> createdAt = const Value.absent(),
            Value<String> updatedAt = const Value.absent(),
            Value<bool> hidden = const Value.absent(),
            Value<bool> disabled = const Value.absent(),
            Value<String?> disabledAt = const Value.absent(),
            Value<String?> tags = const Value.absent(),
          }) =>
              EntityEntitiesCompanion(
            id: id,
            canonicalName: canonicalName,
            entityType: entityType,
            civId: civId,
            description: description,
            firstSeenTurn: firstSeenTurn,
            lastSeenTurn: lastSeenTurn,
            isActive: isActive,
            createdAt: createdAt,
            updatedAt: updatedAt,
            hidden: hidden,
            disabled: disabled,
            disabledAt: disabledAt,
            tags: tags,
          ),
          createCompanionCallback: ({
            Value<int> id = const Value.absent(),
            required String canonicalName,
            required String entityType,
            Value<int?> civId = const Value.absent(),
            Value<String?> description = const Value.absent(),
            Value<int?> firstSeenTurn = const Value.absent(),
            Value<int?> lastSeenTurn = const Value.absent(),
            Value<int> isActive = const Value.absent(),
            required String createdAt,
            required String updatedAt,
            Value<bool> hidden = const Value.absent(),
            Value<bool> disabled = const Value.absent(),
            Value<String?> disabledAt = const Value.absent(),
            Value<String?> tags = const Value.absent(),
          }) =>
              EntityEntitiesCompanion.insert(
            id: id,
            canonicalName: canonicalName,
            entityType: entityType,
            civId: civId,
            description: description,
            firstSeenTurn: firstSeenTurn,
            lastSeenTurn: lastSeenTurn,
            isActive: isActive,
            createdAt: createdAt,
            updatedAt: updatedAt,
            hidden: hidden,
            disabled: disabled,
            disabledAt: disabledAt,
            tags: tags,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$EntityEntitiesTableProcessedTableManager = ProcessedTableManager<
    _$AurelmDatabase,
    $EntityEntitiesTable,
    EntityRow,
    $$EntityEntitiesTableFilterComposer,
    $$EntityEntitiesTableOrderingComposer,
    $$EntityEntitiesTableAnnotationComposer,
    $$EntityEntitiesTableCreateCompanionBuilder,
    $$EntityEntitiesTableUpdateCompanionBuilder,
    (
      EntityRow,
      BaseReferences<_$AurelmDatabase, $EntityEntitiesTable, EntityRow>
    ),
    EntityRow,
    PrefetchHooks Function()>;
typedef $$EntityAliasesTableCreateCompanionBuilder = EntityAliasesCompanion
    Function({
  Value<int> id,
  required int entityId,
  required String alias,
  Value<int?> firstSeenTurnId,
});
typedef $$EntityAliasesTableUpdateCompanionBuilder = EntityAliasesCompanion
    Function({
  Value<int> id,
  Value<int> entityId,
  Value<String> alias,
  Value<int?> firstSeenTurnId,
});

class $$EntityAliasesTableFilterComposer
    extends Composer<_$AurelmDatabase, $EntityAliasesTable> {
  $$EntityAliasesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get entityId => $composableBuilder(
      column: $table.entityId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get alias => $composableBuilder(
      column: $table.alias, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get firstSeenTurnId => $composableBuilder(
      column: $table.firstSeenTurnId,
      builder: (column) => ColumnFilters(column));
}

class $$EntityAliasesTableOrderingComposer
    extends Composer<_$AurelmDatabase, $EntityAliasesTable> {
  $$EntityAliasesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get entityId => $composableBuilder(
      column: $table.entityId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get alias => $composableBuilder(
      column: $table.alias, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get firstSeenTurnId => $composableBuilder(
      column: $table.firstSeenTurnId,
      builder: (column) => ColumnOrderings(column));
}

class $$EntityAliasesTableAnnotationComposer
    extends Composer<_$AurelmDatabase, $EntityAliasesTable> {
  $$EntityAliasesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get entityId =>
      $composableBuilder(column: $table.entityId, builder: (column) => column);

  GeneratedColumn<String> get alias =>
      $composableBuilder(column: $table.alias, builder: (column) => column);

  GeneratedColumn<int> get firstSeenTurnId => $composableBuilder(
      column: $table.firstSeenTurnId, builder: (column) => column);
}

class $$EntityAliasesTableTableManager extends RootTableManager<
    _$AurelmDatabase,
    $EntityAliasesTable,
    AliasRow,
    $$EntityAliasesTableFilterComposer,
    $$EntityAliasesTableOrderingComposer,
    $$EntityAliasesTableAnnotationComposer,
    $$EntityAliasesTableCreateCompanionBuilder,
    $$EntityAliasesTableUpdateCompanionBuilder,
    (AliasRow, BaseReferences<_$AurelmDatabase, $EntityAliasesTable, AliasRow>),
    AliasRow,
    PrefetchHooks Function()> {
  $$EntityAliasesTableTableManager(
      _$AurelmDatabase db, $EntityAliasesTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$EntityAliasesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$EntityAliasesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$EntityAliasesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<int> id = const Value.absent(),
            Value<int> entityId = const Value.absent(),
            Value<String> alias = const Value.absent(),
            Value<int?> firstSeenTurnId = const Value.absent(),
          }) =>
              EntityAliasesCompanion(
            id: id,
            entityId: entityId,
            alias: alias,
            firstSeenTurnId: firstSeenTurnId,
          ),
          createCompanionCallback: ({
            Value<int> id = const Value.absent(),
            required int entityId,
            required String alias,
            Value<int?> firstSeenTurnId = const Value.absent(),
          }) =>
              EntityAliasesCompanion.insert(
            id: id,
            entityId: entityId,
            alias: alias,
            firstSeenTurnId: firstSeenTurnId,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$EntityAliasesTableProcessedTableManager = ProcessedTableManager<
    _$AurelmDatabase,
    $EntityAliasesTable,
    AliasRow,
    $$EntityAliasesTableFilterComposer,
    $$EntityAliasesTableOrderingComposer,
    $$EntityAliasesTableAnnotationComposer,
    $$EntityAliasesTableCreateCompanionBuilder,
    $$EntityAliasesTableUpdateCompanionBuilder,
    (AliasRow, BaseReferences<_$AurelmDatabase, $EntityAliasesTable, AliasRow>),
    AliasRow,
    PrefetchHooks Function()>;
typedef $$EntityMentionsTableCreateCompanionBuilder = EntityMentionsCompanion
    Function({
  Value<int> id,
  required int entityId,
  required int turnId,
  Value<int?> segmentId,
  required String mentionText,
  Value<String?> context,
  Value<String> source,
});
typedef $$EntityMentionsTableUpdateCompanionBuilder = EntityMentionsCompanion
    Function({
  Value<int> id,
  Value<int> entityId,
  Value<int> turnId,
  Value<int?> segmentId,
  Value<String> mentionText,
  Value<String?> context,
  Value<String> source,
});

class $$EntityMentionsTableFilterComposer
    extends Composer<_$AurelmDatabase, $EntityMentionsTable> {
  $$EntityMentionsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get entityId => $composableBuilder(
      column: $table.entityId, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get turnId => $composableBuilder(
      column: $table.turnId, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get segmentId => $composableBuilder(
      column: $table.segmentId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get mentionText => $composableBuilder(
      column: $table.mentionText, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get context => $composableBuilder(
      column: $table.context, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get source => $composableBuilder(
      column: $table.source, builder: (column) => ColumnFilters(column));
}

class $$EntityMentionsTableOrderingComposer
    extends Composer<_$AurelmDatabase, $EntityMentionsTable> {
  $$EntityMentionsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get entityId => $composableBuilder(
      column: $table.entityId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get turnId => $composableBuilder(
      column: $table.turnId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get segmentId => $composableBuilder(
      column: $table.segmentId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get mentionText => $composableBuilder(
      column: $table.mentionText, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get context => $composableBuilder(
      column: $table.context, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get source => $composableBuilder(
      column: $table.source, builder: (column) => ColumnOrderings(column));
}

class $$EntityMentionsTableAnnotationComposer
    extends Composer<_$AurelmDatabase, $EntityMentionsTable> {
  $$EntityMentionsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get entityId =>
      $composableBuilder(column: $table.entityId, builder: (column) => column);

  GeneratedColumn<int> get turnId =>
      $composableBuilder(column: $table.turnId, builder: (column) => column);

  GeneratedColumn<int> get segmentId =>
      $composableBuilder(column: $table.segmentId, builder: (column) => column);

  GeneratedColumn<String> get mentionText => $composableBuilder(
      column: $table.mentionText, builder: (column) => column);

  GeneratedColumn<String> get context =>
      $composableBuilder(column: $table.context, builder: (column) => column);

  GeneratedColumn<String> get source =>
      $composableBuilder(column: $table.source, builder: (column) => column);
}

class $$EntityMentionsTableTableManager extends RootTableManager<
    _$AurelmDatabase,
    $EntityMentionsTable,
    MentionRow,
    $$EntityMentionsTableFilterComposer,
    $$EntityMentionsTableOrderingComposer,
    $$EntityMentionsTableAnnotationComposer,
    $$EntityMentionsTableCreateCompanionBuilder,
    $$EntityMentionsTableUpdateCompanionBuilder,
    (
      MentionRow,
      BaseReferences<_$AurelmDatabase, $EntityMentionsTable, MentionRow>
    ),
    MentionRow,
    PrefetchHooks Function()> {
  $$EntityMentionsTableTableManager(
      _$AurelmDatabase db, $EntityMentionsTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$EntityMentionsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$EntityMentionsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$EntityMentionsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<int> id = const Value.absent(),
            Value<int> entityId = const Value.absent(),
            Value<int> turnId = const Value.absent(),
            Value<int?> segmentId = const Value.absent(),
            Value<String> mentionText = const Value.absent(),
            Value<String?> context = const Value.absent(),
            Value<String> source = const Value.absent(),
          }) =>
              EntityMentionsCompanion(
            id: id,
            entityId: entityId,
            turnId: turnId,
            segmentId: segmentId,
            mentionText: mentionText,
            context: context,
            source: source,
          ),
          createCompanionCallback: ({
            Value<int> id = const Value.absent(),
            required int entityId,
            required int turnId,
            Value<int?> segmentId = const Value.absent(),
            required String mentionText,
            Value<String?> context = const Value.absent(),
            Value<String> source = const Value.absent(),
          }) =>
              EntityMentionsCompanion.insert(
            id: id,
            entityId: entityId,
            turnId: turnId,
            segmentId: segmentId,
            mentionText: mentionText,
            context: context,
            source: source,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$EntityMentionsTableProcessedTableManager = ProcessedTableManager<
    _$AurelmDatabase,
    $EntityMentionsTable,
    MentionRow,
    $$EntityMentionsTableFilterComposer,
    $$EntityMentionsTableOrderingComposer,
    $$EntityMentionsTableAnnotationComposer,
    $$EntityMentionsTableCreateCompanionBuilder,
    $$EntityMentionsTableUpdateCompanionBuilder,
    (
      MentionRow,
      BaseReferences<_$AurelmDatabase, $EntityMentionsTable, MentionRow>
    ),
    MentionRow,
    PrefetchHooks Function()>;
typedef $$EntityRelationsTableCreateCompanionBuilder = EntityRelationsCompanion
    Function({
  Value<int> id,
  required int sourceEntityId,
  required int targetEntityId,
  required String relationType,
  Value<String?> description,
  Value<int?> turnId,
  Value<int> isActive,
  required String createdAt,
});
typedef $$EntityRelationsTableUpdateCompanionBuilder = EntityRelationsCompanion
    Function({
  Value<int> id,
  Value<int> sourceEntityId,
  Value<int> targetEntityId,
  Value<String> relationType,
  Value<String?> description,
  Value<int?> turnId,
  Value<int> isActive,
  Value<String> createdAt,
});

class $$EntityRelationsTableFilterComposer
    extends Composer<_$AurelmDatabase, $EntityRelationsTable> {
  $$EntityRelationsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get sourceEntityId => $composableBuilder(
      column: $table.sourceEntityId,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get targetEntityId => $composableBuilder(
      column: $table.targetEntityId,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get relationType => $composableBuilder(
      column: $table.relationType, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get turnId => $composableBuilder(
      column: $table.turnId, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get isActive => $composableBuilder(
      column: $table.isActive, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnFilters(column));
}

class $$EntityRelationsTableOrderingComposer
    extends Composer<_$AurelmDatabase, $EntityRelationsTable> {
  $$EntityRelationsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get sourceEntityId => $composableBuilder(
      column: $table.sourceEntityId,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get targetEntityId => $composableBuilder(
      column: $table.targetEntityId,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get relationType => $composableBuilder(
      column: $table.relationType,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get turnId => $composableBuilder(
      column: $table.turnId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get isActive => $composableBuilder(
      column: $table.isActive, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnOrderings(column));
}

class $$EntityRelationsTableAnnotationComposer
    extends Composer<_$AurelmDatabase, $EntityRelationsTable> {
  $$EntityRelationsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get sourceEntityId => $composableBuilder(
      column: $table.sourceEntityId, builder: (column) => column);

  GeneratedColumn<int> get targetEntityId => $composableBuilder(
      column: $table.targetEntityId, builder: (column) => column);

  GeneratedColumn<String> get relationType => $composableBuilder(
      column: $table.relationType, builder: (column) => column);

  GeneratedColumn<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => column);

  GeneratedColumn<int> get turnId =>
      $composableBuilder(column: $table.turnId, builder: (column) => column);

  GeneratedColumn<int> get isActive =>
      $composableBuilder(column: $table.isActive, builder: (column) => column);

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);
}

class $$EntityRelationsTableTableManager extends RootTableManager<
    _$AurelmDatabase,
    $EntityRelationsTable,
    RelationRow,
    $$EntityRelationsTableFilterComposer,
    $$EntityRelationsTableOrderingComposer,
    $$EntityRelationsTableAnnotationComposer,
    $$EntityRelationsTableCreateCompanionBuilder,
    $$EntityRelationsTableUpdateCompanionBuilder,
    (
      RelationRow,
      BaseReferences<_$AurelmDatabase, $EntityRelationsTable, RelationRow>
    ),
    RelationRow,
    PrefetchHooks Function()> {
  $$EntityRelationsTableTableManager(
      _$AurelmDatabase db, $EntityRelationsTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$EntityRelationsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$EntityRelationsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$EntityRelationsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<int> id = const Value.absent(),
            Value<int> sourceEntityId = const Value.absent(),
            Value<int> targetEntityId = const Value.absent(),
            Value<String> relationType = const Value.absent(),
            Value<String?> description = const Value.absent(),
            Value<int?> turnId = const Value.absent(),
            Value<int> isActive = const Value.absent(),
            Value<String> createdAt = const Value.absent(),
          }) =>
              EntityRelationsCompanion(
            id: id,
            sourceEntityId: sourceEntityId,
            targetEntityId: targetEntityId,
            relationType: relationType,
            description: description,
            turnId: turnId,
            isActive: isActive,
            createdAt: createdAt,
          ),
          createCompanionCallback: ({
            Value<int> id = const Value.absent(),
            required int sourceEntityId,
            required int targetEntityId,
            required String relationType,
            Value<String?> description = const Value.absent(),
            Value<int?> turnId = const Value.absent(),
            Value<int> isActive = const Value.absent(),
            required String createdAt,
          }) =>
              EntityRelationsCompanion.insert(
            id: id,
            sourceEntityId: sourceEntityId,
            targetEntityId: targetEntityId,
            relationType: relationType,
            description: description,
            turnId: turnId,
            isActive: isActive,
            createdAt: createdAt,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$EntityRelationsTableProcessedTableManager = ProcessedTableManager<
    _$AurelmDatabase,
    $EntityRelationsTable,
    RelationRow,
    $$EntityRelationsTableFilterComposer,
    $$EntityRelationsTableOrderingComposer,
    $$EntityRelationsTableAnnotationComposer,
    $$EntityRelationsTableCreateCompanionBuilder,
    $$EntityRelationsTableUpdateCompanionBuilder,
    (
      RelationRow,
      BaseReferences<_$AurelmDatabase, $EntityRelationsTable, RelationRow>
    ),
    RelationRow,
    PrefetchHooks Function()>;
typedef $$PipelineRunsTableCreateCompanionBuilder = PipelineRunsCompanion
    Function({
  Value<int> id,
  required String startedAt,
  Value<String?> completedAt,
  Value<String> status,
  Value<int?> messagesProcessed,
  Value<int?> turnsCreated,
  Value<int?> entitiesExtracted,
  Value<String?> errorMessage,
});
typedef $$PipelineRunsTableUpdateCompanionBuilder = PipelineRunsCompanion
    Function({
  Value<int> id,
  Value<String> startedAt,
  Value<String?> completedAt,
  Value<String> status,
  Value<int?> messagesProcessed,
  Value<int?> turnsCreated,
  Value<int?> entitiesExtracted,
  Value<String?> errorMessage,
});

class $$PipelineRunsTableFilterComposer
    extends Composer<_$AurelmDatabase, $PipelineRunsTable> {
  $$PipelineRunsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get startedAt => $composableBuilder(
      column: $table.startedAt, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get completedAt => $composableBuilder(
      column: $table.completedAt, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get status => $composableBuilder(
      column: $table.status, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get messagesProcessed => $composableBuilder(
      column: $table.messagesProcessed,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get turnsCreated => $composableBuilder(
      column: $table.turnsCreated, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get entitiesExtracted => $composableBuilder(
      column: $table.entitiesExtracted,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get errorMessage => $composableBuilder(
      column: $table.errorMessage, builder: (column) => ColumnFilters(column));
}

class $$PipelineRunsTableOrderingComposer
    extends Composer<_$AurelmDatabase, $PipelineRunsTable> {
  $$PipelineRunsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get startedAt => $composableBuilder(
      column: $table.startedAt, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get completedAt => $composableBuilder(
      column: $table.completedAt, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get status => $composableBuilder(
      column: $table.status, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get messagesProcessed => $composableBuilder(
      column: $table.messagesProcessed,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get turnsCreated => $composableBuilder(
      column: $table.turnsCreated,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get entitiesExtracted => $composableBuilder(
      column: $table.entitiesExtracted,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get errorMessage => $composableBuilder(
      column: $table.errorMessage,
      builder: (column) => ColumnOrderings(column));
}

class $$PipelineRunsTableAnnotationComposer
    extends Composer<_$AurelmDatabase, $PipelineRunsTable> {
  $$PipelineRunsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get startedAt =>
      $composableBuilder(column: $table.startedAt, builder: (column) => column);

  GeneratedColumn<String> get completedAt => $composableBuilder(
      column: $table.completedAt, builder: (column) => column);

  GeneratedColumn<String> get status =>
      $composableBuilder(column: $table.status, builder: (column) => column);

  GeneratedColumn<int> get messagesProcessed => $composableBuilder(
      column: $table.messagesProcessed, builder: (column) => column);

  GeneratedColumn<int> get turnsCreated => $composableBuilder(
      column: $table.turnsCreated, builder: (column) => column);

  GeneratedColumn<int> get entitiesExtracted => $composableBuilder(
      column: $table.entitiesExtracted, builder: (column) => column);

  GeneratedColumn<String> get errorMessage => $composableBuilder(
      column: $table.errorMessage, builder: (column) => column);
}

class $$PipelineRunsTableTableManager extends RootTableManager<
    _$AurelmDatabase,
    $PipelineRunsTable,
    PipelineRunRow,
    $$PipelineRunsTableFilterComposer,
    $$PipelineRunsTableOrderingComposer,
    $$PipelineRunsTableAnnotationComposer,
    $$PipelineRunsTableCreateCompanionBuilder,
    $$PipelineRunsTableUpdateCompanionBuilder,
    (
      PipelineRunRow,
      BaseReferences<_$AurelmDatabase, $PipelineRunsTable, PipelineRunRow>
    ),
    PipelineRunRow,
    PrefetchHooks Function()> {
  $$PipelineRunsTableTableManager(_$AurelmDatabase db, $PipelineRunsTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$PipelineRunsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$PipelineRunsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$PipelineRunsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<int> id = const Value.absent(),
            Value<String> startedAt = const Value.absent(),
            Value<String?> completedAt = const Value.absent(),
            Value<String> status = const Value.absent(),
            Value<int?> messagesProcessed = const Value.absent(),
            Value<int?> turnsCreated = const Value.absent(),
            Value<int?> entitiesExtracted = const Value.absent(),
            Value<String?> errorMessage = const Value.absent(),
          }) =>
              PipelineRunsCompanion(
            id: id,
            startedAt: startedAt,
            completedAt: completedAt,
            status: status,
            messagesProcessed: messagesProcessed,
            turnsCreated: turnsCreated,
            entitiesExtracted: entitiesExtracted,
            errorMessage: errorMessage,
          ),
          createCompanionCallback: ({
            Value<int> id = const Value.absent(),
            required String startedAt,
            Value<String?> completedAt = const Value.absent(),
            Value<String> status = const Value.absent(),
            Value<int?> messagesProcessed = const Value.absent(),
            Value<int?> turnsCreated = const Value.absent(),
            Value<int?> entitiesExtracted = const Value.absent(),
            Value<String?> errorMessage = const Value.absent(),
          }) =>
              PipelineRunsCompanion.insert(
            id: id,
            startedAt: startedAt,
            completedAt: completedAt,
            status: status,
            messagesProcessed: messagesProcessed,
            turnsCreated: turnsCreated,
            entitiesExtracted: entitiesExtracted,
            errorMessage: errorMessage,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$PipelineRunsTableProcessedTableManager = ProcessedTableManager<
    _$AurelmDatabase,
    $PipelineRunsTable,
    PipelineRunRow,
    $$PipelineRunsTableFilterComposer,
    $$PipelineRunsTableOrderingComposer,
    $$PipelineRunsTableAnnotationComposer,
    $$PipelineRunsTableCreateCompanionBuilder,
    $$PipelineRunsTableUpdateCompanionBuilder,
    (
      PipelineRunRow,
      BaseReferences<_$AurelmDatabase, $PipelineRunsTable, PipelineRunRow>
    ),
    PipelineRunRow,
    PrefetchHooks Function()>;
typedef $$SubjectSubjectsTableCreateCompanionBuilder = SubjectSubjectsCompanion
    Function({
  Value<int> id,
  required int civId,
  Value<int?> sourceTurnId,
  required String direction,
  required String title,
  Value<String?> description,
  Value<String?> sourceQuote,
  required String category,
  Value<String> status,
  Value<String> tags,
  required String createdAt,
  required String updatedAt,
});
typedef $$SubjectSubjectsTableUpdateCompanionBuilder = SubjectSubjectsCompanion
    Function({
  Value<int> id,
  Value<int> civId,
  Value<int?> sourceTurnId,
  Value<String> direction,
  Value<String> title,
  Value<String?> description,
  Value<String?> sourceQuote,
  Value<String> category,
  Value<String> status,
  Value<String> tags,
  Value<String> createdAt,
  Value<String> updatedAt,
});

class $$SubjectSubjectsTableFilterComposer
    extends Composer<_$AurelmDatabase, $SubjectSubjectsTable> {
  $$SubjectSubjectsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get civId => $composableBuilder(
      column: $table.civId, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get sourceTurnId => $composableBuilder(
      column: $table.sourceTurnId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get direction => $composableBuilder(
      column: $table.direction, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get title => $composableBuilder(
      column: $table.title, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get sourceQuote => $composableBuilder(
      column: $table.sourceQuote, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get category => $composableBuilder(
      column: $table.category, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get status => $composableBuilder(
      column: $table.status, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get tags => $composableBuilder(
      column: $table.tags, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get updatedAt => $composableBuilder(
      column: $table.updatedAt, builder: (column) => ColumnFilters(column));
}

class $$SubjectSubjectsTableOrderingComposer
    extends Composer<_$AurelmDatabase, $SubjectSubjectsTable> {
  $$SubjectSubjectsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get civId => $composableBuilder(
      column: $table.civId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get sourceTurnId => $composableBuilder(
      column: $table.sourceTurnId,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get direction => $composableBuilder(
      column: $table.direction, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get title => $composableBuilder(
      column: $table.title, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get sourceQuote => $composableBuilder(
      column: $table.sourceQuote, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get category => $composableBuilder(
      column: $table.category, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get status => $composableBuilder(
      column: $table.status, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get tags => $composableBuilder(
      column: $table.tags, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get updatedAt => $composableBuilder(
      column: $table.updatedAt, builder: (column) => ColumnOrderings(column));
}

class $$SubjectSubjectsTableAnnotationComposer
    extends Composer<_$AurelmDatabase, $SubjectSubjectsTable> {
  $$SubjectSubjectsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get civId =>
      $composableBuilder(column: $table.civId, builder: (column) => column);

  GeneratedColumn<int> get sourceTurnId => $composableBuilder(
      column: $table.sourceTurnId, builder: (column) => column);

  GeneratedColumn<String> get direction =>
      $composableBuilder(column: $table.direction, builder: (column) => column);

  GeneratedColumn<String> get title =>
      $composableBuilder(column: $table.title, builder: (column) => column);

  GeneratedColumn<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => column);

  GeneratedColumn<String> get sourceQuote => $composableBuilder(
      column: $table.sourceQuote, builder: (column) => column);

  GeneratedColumn<String> get category =>
      $composableBuilder(column: $table.category, builder: (column) => column);

  GeneratedColumn<String> get status =>
      $composableBuilder(column: $table.status, builder: (column) => column);

  GeneratedColumn<String> get tags =>
      $composableBuilder(column: $table.tags, builder: (column) => column);

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  GeneratedColumn<String> get updatedAt =>
      $composableBuilder(column: $table.updatedAt, builder: (column) => column);
}

class $$SubjectSubjectsTableTableManager extends RootTableManager<
    _$AurelmDatabase,
    $SubjectSubjectsTable,
    SubjectRow,
    $$SubjectSubjectsTableFilterComposer,
    $$SubjectSubjectsTableOrderingComposer,
    $$SubjectSubjectsTableAnnotationComposer,
    $$SubjectSubjectsTableCreateCompanionBuilder,
    $$SubjectSubjectsTableUpdateCompanionBuilder,
    (
      SubjectRow,
      BaseReferences<_$AurelmDatabase, $SubjectSubjectsTable, SubjectRow>
    ),
    SubjectRow,
    PrefetchHooks Function()> {
  $$SubjectSubjectsTableTableManager(
      _$AurelmDatabase db, $SubjectSubjectsTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$SubjectSubjectsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$SubjectSubjectsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$SubjectSubjectsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<int> id = const Value.absent(),
            Value<int> civId = const Value.absent(),
            Value<int?> sourceTurnId = const Value.absent(),
            Value<String> direction = const Value.absent(),
            Value<String> title = const Value.absent(),
            Value<String?> description = const Value.absent(),
            Value<String?> sourceQuote = const Value.absent(),
            Value<String> category = const Value.absent(),
            Value<String> status = const Value.absent(),
            Value<String> tags = const Value.absent(),
            Value<String> createdAt = const Value.absent(),
            Value<String> updatedAt = const Value.absent(),
          }) =>
              SubjectSubjectsCompanion(
            id: id,
            civId: civId,
            sourceTurnId: sourceTurnId,
            direction: direction,
            title: title,
            description: description,
            sourceQuote: sourceQuote,
            category: category,
            status: status,
            tags: tags,
            createdAt: createdAt,
            updatedAt: updatedAt,
          ),
          createCompanionCallback: ({
            Value<int> id = const Value.absent(),
            required int civId,
            Value<int?> sourceTurnId = const Value.absent(),
            required String direction,
            required String title,
            Value<String?> description = const Value.absent(),
            Value<String?> sourceQuote = const Value.absent(),
            required String category,
            Value<String> status = const Value.absent(),
            Value<String> tags = const Value.absent(),
            required String createdAt,
            required String updatedAt,
          }) =>
              SubjectSubjectsCompanion.insert(
            id: id,
            civId: civId,
            sourceTurnId: sourceTurnId,
            direction: direction,
            title: title,
            description: description,
            sourceQuote: sourceQuote,
            category: category,
            status: status,
            tags: tags,
            createdAt: createdAt,
            updatedAt: updatedAt,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$SubjectSubjectsTableProcessedTableManager = ProcessedTableManager<
    _$AurelmDatabase,
    $SubjectSubjectsTable,
    SubjectRow,
    $$SubjectSubjectsTableFilterComposer,
    $$SubjectSubjectsTableOrderingComposer,
    $$SubjectSubjectsTableAnnotationComposer,
    $$SubjectSubjectsTableCreateCompanionBuilder,
    $$SubjectSubjectsTableUpdateCompanionBuilder,
    (
      SubjectRow,
      BaseReferences<_$AurelmDatabase, $SubjectSubjectsTable, SubjectRow>
    ),
    SubjectRow,
    PrefetchHooks Function()>;
typedef $$SubjectOptionsTableCreateCompanionBuilder = SubjectOptionsCompanion
    Function({
  Value<int> id,
  required int subjectId,
  required int optionNumber,
  required String label,
  Value<String?> description,
  Value<bool> isLibre,
});
typedef $$SubjectOptionsTableUpdateCompanionBuilder = SubjectOptionsCompanion
    Function({
  Value<int> id,
  Value<int> subjectId,
  Value<int> optionNumber,
  Value<String> label,
  Value<String?> description,
  Value<bool> isLibre,
});

class $$SubjectOptionsTableFilterComposer
    extends Composer<_$AurelmDatabase, $SubjectOptionsTable> {
  $$SubjectOptionsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get subjectId => $composableBuilder(
      column: $table.subjectId, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get optionNumber => $composableBuilder(
      column: $table.optionNumber, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get label => $composableBuilder(
      column: $table.label, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isLibre => $composableBuilder(
      column: $table.isLibre, builder: (column) => ColumnFilters(column));
}

class $$SubjectOptionsTableOrderingComposer
    extends Composer<_$AurelmDatabase, $SubjectOptionsTable> {
  $$SubjectOptionsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get subjectId => $composableBuilder(
      column: $table.subjectId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get optionNumber => $composableBuilder(
      column: $table.optionNumber,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get label => $composableBuilder(
      column: $table.label, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isLibre => $composableBuilder(
      column: $table.isLibre, builder: (column) => ColumnOrderings(column));
}

class $$SubjectOptionsTableAnnotationComposer
    extends Composer<_$AurelmDatabase, $SubjectOptionsTable> {
  $$SubjectOptionsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get subjectId =>
      $composableBuilder(column: $table.subjectId, builder: (column) => column);

  GeneratedColumn<int> get optionNumber => $composableBuilder(
      column: $table.optionNumber, builder: (column) => column);

  GeneratedColumn<String> get label =>
      $composableBuilder(column: $table.label, builder: (column) => column);

  GeneratedColumn<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => column);

  GeneratedColumn<bool> get isLibre =>
      $composableBuilder(column: $table.isLibre, builder: (column) => column);
}

class $$SubjectOptionsTableTableManager extends RootTableManager<
    _$AurelmDatabase,
    $SubjectOptionsTable,
    SubjectOptionRow,
    $$SubjectOptionsTableFilterComposer,
    $$SubjectOptionsTableOrderingComposer,
    $$SubjectOptionsTableAnnotationComposer,
    $$SubjectOptionsTableCreateCompanionBuilder,
    $$SubjectOptionsTableUpdateCompanionBuilder,
    (
      SubjectOptionRow,
      BaseReferences<_$AurelmDatabase, $SubjectOptionsTable, SubjectOptionRow>
    ),
    SubjectOptionRow,
    PrefetchHooks Function()> {
  $$SubjectOptionsTableTableManager(
      _$AurelmDatabase db, $SubjectOptionsTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$SubjectOptionsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$SubjectOptionsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$SubjectOptionsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<int> id = const Value.absent(),
            Value<int> subjectId = const Value.absent(),
            Value<int> optionNumber = const Value.absent(),
            Value<String> label = const Value.absent(),
            Value<String?> description = const Value.absent(),
            Value<bool> isLibre = const Value.absent(),
          }) =>
              SubjectOptionsCompanion(
            id: id,
            subjectId: subjectId,
            optionNumber: optionNumber,
            label: label,
            description: description,
            isLibre: isLibre,
          ),
          createCompanionCallback: ({
            Value<int> id = const Value.absent(),
            required int subjectId,
            required int optionNumber,
            required String label,
            Value<String?> description = const Value.absent(),
            Value<bool> isLibre = const Value.absent(),
          }) =>
              SubjectOptionsCompanion.insert(
            id: id,
            subjectId: subjectId,
            optionNumber: optionNumber,
            label: label,
            description: description,
            isLibre: isLibre,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$SubjectOptionsTableProcessedTableManager = ProcessedTableManager<
    _$AurelmDatabase,
    $SubjectOptionsTable,
    SubjectOptionRow,
    $$SubjectOptionsTableFilterComposer,
    $$SubjectOptionsTableOrderingComposer,
    $$SubjectOptionsTableAnnotationComposer,
    $$SubjectOptionsTableCreateCompanionBuilder,
    $$SubjectOptionsTableUpdateCompanionBuilder,
    (
      SubjectOptionRow,
      BaseReferences<_$AurelmDatabase, $SubjectOptionsTable, SubjectOptionRow>
    ),
    SubjectOptionRow,
    PrefetchHooks Function()>;
typedef $$SubjectResolutionsTableCreateCompanionBuilder
    = SubjectResolutionsCompanion Function({
  Value<int> id,
  required int subjectId,
  required int resolvedByTurnId,
  Value<int?> chosenOptionId,
  required String resolutionText,
  Value<String?> sourceQuote,
  Value<bool> isLibre,
  Value<double> confidence,
  required String createdAt,
});
typedef $$SubjectResolutionsTableUpdateCompanionBuilder
    = SubjectResolutionsCompanion Function({
  Value<int> id,
  Value<int> subjectId,
  Value<int> resolvedByTurnId,
  Value<int?> chosenOptionId,
  Value<String> resolutionText,
  Value<String?> sourceQuote,
  Value<bool> isLibre,
  Value<double> confidence,
  Value<String> createdAt,
});

class $$SubjectResolutionsTableFilterComposer
    extends Composer<_$AurelmDatabase, $SubjectResolutionsTable> {
  $$SubjectResolutionsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get subjectId => $composableBuilder(
      column: $table.subjectId, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get resolvedByTurnId => $composableBuilder(
      column: $table.resolvedByTurnId,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get chosenOptionId => $composableBuilder(
      column: $table.chosenOptionId,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get resolutionText => $composableBuilder(
      column: $table.resolutionText,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get sourceQuote => $composableBuilder(
      column: $table.sourceQuote, builder: (column) => ColumnFilters(column));

  ColumnFilters<bool> get isLibre => $composableBuilder(
      column: $table.isLibre, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get confidence => $composableBuilder(
      column: $table.confidence, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnFilters(column));
}

class $$SubjectResolutionsTableOrderingComposer
    extends Composer<_$AurelmDatabase, $SubjectResolutionsTable> {
  $$SubjectResolutionsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get subjectId => $composableBuilder(
      column: $table.subjectId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get resolvedByTurnId => $composableBuilder(
      column: $table.resolvedByTurnId,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get chosenOptionId => $composableBuilder(
      column: $table.chosenOptionId,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get resolutionText => $composableBuilder(
      column: $table.resolutionText,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get sourceQuote => $composableBuilder(
      column: $table.sourceQuote, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<bool> get isLibre => $composableBuilder(
      column: $table.isLibre, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get confidence => $composableBuilder(
      column: $table.confidence, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnOrderings(column));
}

class $$SubjectResolutionsTableAnnotationComposer
    extends Composer<_$AurelmDatabase, $SubjectResolutionsTable> {
  $$SubjectResolutionsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get subjectId =>
      $composableBuilder(column: $table.subjectId, builder: (column) => column);

  GeneratedColumn<int> get resolvedByTurnId => $composableBuilder(
      column: $table.resolvedByTurnId, builder: (column) => column);

  GeneratedColumn<int> get chosenOptionId => $composableBuilder(
      column: $table.chosenOptionId, builder: (column) => column);

  GeneratedColumn<String> get resolutionText => $composableBuilder(
      column: $table.resolutionText, builder: (column) => column);

  GeneratedColumn<String> get sourceQuote => $composableBuilder(
      column: $table.sourceQuote, builder: (column) => column);

  GeneratedColumn<bool> get isLibre =>
      $composableBuilder(column: $table.isLibre, builder: (column) => column);

  GeneratedColumn<double> get confidence => $composableBuilder(
      column: $table.confidence, builder: (column) => column);

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);
}

class $$SubjectResolutionsTableTableManager extends RootTableManager<
    _$AurelmDatabase,
    $SubjectResolutionsTable,
    SubjectResolutionRow,
    $$SubjectResolutionsTableFilterComposer,
    $$SubjectResolutionsTableOrderingComposer,
    $$SubjectResolutionsTableAnnotationComposer,
    $$SubjectResolutionsTableCreateCompanionBuilder,
    $$SubjectResolutionsTableUpdateCompanionBuilder,
    (
      SubjectResolutionRow,
      BaseReferences<_$AurelmDatabase, $SubjectResolutionsTable,
          SubjectResolutionRow>
    ),
    SubjectResolutionRow,
    PrefetchHooks Function()> {
  $$SubjectResolutionsTableTableManager(
      _$AurelmDatabase db, $SubjectResolutionsTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$SubjectResolutionsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$SubjectResolutionsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$SubjectResolutionsTableAnnotationComposer(
                  $db: db, $table: table),
          updateCompanionCallback: ({
            Value<int> id = const Value.absent(),
            Value<int> subjectId = const Value.absent(),
            Value<int> resolvedByTurnId = const Value.absent(),
            Value<int?> chosenOptionId = const Value.absent(),
            Value<String> resolutionText = const Value.absent(),
            Value<String?> sourceQuote = const Value.absent(),
            Value<bool> isLibre = const Value.absent(),
            Value<double> confidence = const Value.absent(),
            Value<String> createdAt = const Value.absent(),
          }) =>
              SubjectResolutionsCompanion(
            id: id,
            subjectId: subjectId,
            resolvedByTurnId: resolvedByTurnId,
            chosenOptionId: chosenOptionId,
            resolutionText: resolutionText,
            sourceQuote: sourceQuote,
            isLibre: isLibre,
            confidence: confidence,
            createdAt: createdAt,
          ),
          createCompanionCallback: ({
            Value<int> id = const Value.absent(),
            required int subjectId,
            required int resolvedByTurnId,
            Value<int?> chosenOptionId = const Value.absent(),
            required String resolutionText,
            Value<String?> sourceQuote = const Value.absent(),
            Value<bool> isLibre = const Value.absent(),
            Value<double> confidence = const Value.absent(),
            required String createdAt,
          }) =>
              SubjectResolutionsCompanion.insert(
            id: id,
            subjectId: subjectId,
            resolvedByTurnId: resolvedByTurnId,
            chosenOptionId: chosenOptionId,
            resolutionText: resolutionText,
            sourceQuote: sourceQuote,
            isLibre: isLibre,
            confidence: confidence,
            createdAt: createdAt,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$SubjectResolutionsTableProcessedTableManager = ProcessedTableManager<
    _$AurelmDatabase,
    $SubjectResolutionsTable,
    SubjectResolutionRow,
    $$SubjectResolutionsTableFilterComposer,
    $$SubjectResolutionsTableOrderingComposer,
    $$SubjectResolutionsTableAnnotationComposer,
    $$SubjectResolutionsTableCreateCompanionBuilder,
    $$SubjectResolutionsTableUpdateCompanionBuilder,
    (
      SubjectResolutionRow,
      BaseReferences<_$AurelmDatabase, $SubjectResolutionsTable,
          SubjectResolutionRow>
    ),
    SubjectResolutionRow,
    PrefetchHooks Function()>;
typedef $$NotesTableCreateCompanionBuilder = NotesCompanion Function({
  Value<int> id,
  Value<int?> entityId,
  Value<int?> subjectId,
  Value<int?> turnId,
  Value<int?> civId,
  Value<String> title,
  Value<String> content,
  Value<int> pinned,
  Value<String> noteType,
  required String createdAt,
  required String updatedAt,
});
typedef $$NotesTableUpdateCompanionBuilder = NotesCompanion Function({
  Value<int> id,
  Value<int?> entityId,
  Value<int?> subjectId,
  Value<int?> turnId,
  Value<int?> civId,
  Value<String> title,
  Value<String> content,
  Value<int> pinned,
  Value<String> noteType,
  Value<String> createdAt,
  Value<String> updatedAt,
});

class $$NotesTableFilterComposer
    extends Composer<_$AurelmDatabase, $NotesTable> {
  $$NotesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get entityId => $composableBuilder(
      column: $table.entityId, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get subjectId => $composableBuilder(
      column: $table.subjectId, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get turnId => $composableBuilder(
      column: $table.turnId, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get civId => $composableBuilder(
      column: $table.civId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get title => $composableBuilder(
      column: $table.title, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get content => $composableBuilder(
      column: $table.content, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get pinned => $composableBuilder(
      column: $table.pinned, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get noteType => $composableBuilder(
      column: $table.noteType, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get updatedAt => $composableBuilder(
      column: $table.updatedAt, builder: (column) => ColumnFilters(column));
}

class $$NotesTableOrderingComposer
    extends Composer<_$AurelmDatabase, $NotesTable> {
  $$NotesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get entityId => $composableBuilder(
      column: $table.entityId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get subjectId => $composableBuilder(
      column: $table.subjectId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get turnId => $composableBuilder(
      column: $table.turnId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get civId => $composableBuilder(
      column: $table.civId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get title => $composableBuilder(
      column: $table.title, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get content => $composableBuilder(
      column: $table.content, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get pinned => $composableBuilder(
      column: $table.pinned, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get noteType => $composableBuilder(
      column: $table.noteType, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get updatedAt => $composableBuilder(
      column: $table.updatedAt, builder: (column) => ColumnOrderings(column));
}

class $$NotesTableAnnotationComposer
    extends Composer<_$AurelmDatabase, $NotesTable> {
  $$NotesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get entityId =>
      $composableBuilder(column: $table.entityId, builder: (column) => column);

  GeneratedColumn<int> get subjectId =>
      $composableBuilder(column: $table.subjectId, builder: (column) => column);

  GeneratedColumn<int> get turnId =>
      $composableBuilder(column: $table.turnId, builder: (column) => column);

  GeneratedColumn<int> get civId =>
      $composableBuilder(column: $table.civId, builder: (column) => column);

  GeneratedColumn<String> get title =>
      $composableBuilder(column: $table.title, builder: (column) => column);

  GeneratedColumn<String> get content =>
      $composableBuilder(column: $table.content, builder: (column) => column);

  GeneratedColumn<int> get pinned =>
      $composableBuilder(column: $table.pinned, builder: (column) => column);

  GeneratedColumn<String> get noteType =>
      $composableBuilder(column: $table.noteType, builder: (column) => column);

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  GeneratedColumn<String> get updatedAt =>
      $composableBuilder(column: $table.updatedAt, builder: (column) => column);
}

class $$NotesTableTableManager extends RootTableManager<
    _$AurelmDatabase,
    $NotesTable,
    NoteRow,
    $$NotesTableFilterComposer,
    $$NotesTableOrderingComposer,
    $$NotesTableAnnotationComposer,
    $$NotesTableCreateCompanionBuilder,
    $$NotesTableUpdateCompanionBuilder,
    (NoteRow, BaseReferences<_$AurelmDatabase, $NotesTable, NoteRow>),
    NoteRow,
    PrefetchHooks Function()> {
  $$NotesTableTableManager(_$AurelmDatabase db, $NotesTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$NotesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$NotesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$NotesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<int> id = const Value.absent(),
            Value<int?> entityId = const Value.absent(),
            Value<int?> subjectId = const Value.absent(),
            Value<int?> turnId = const Value.absent(),
            Value<int?> civId = const Value.absent(),
            Value<String> title = const Value.absent(),
            Value<String> content = const Value.absent(),
            Value<int> pinned = const Value.absent(),
            Value<String> noteType = const Value.absent(),
            Value<String> createdAt = const Value.absent(),
            Value<String> updatedAt = const Value.absent(),
          }) =>
              NotesCompanion(
            id: id,
            entityId: entityId,
            subjectId: subjectId,
            turnId: turnId,
            civId: civId,
            title: title,
            content: content,
            pinned: pinned,
            noteType: noteType,
            createdAt: createdAt,
            updatedAt: updatedAt,
          ),
          createCompanionCallback: ({
            Value<int> id = const Value.absent(),
            Value<int?> entityId = const Value.absent(),
            Value<int?> subjectId = const Value.absent(),
            Value<int?> turnId = const Value.absent(),
            Value<int?> civId = const Value.absent(),
            Value<String> title = const Value.absent(),
            Value<String> content = const Value.absent(),
            Value<int> pinned = const Value.absent(),
            Value<String> noteType = const Value.absent(),
            required String createdAt,
            required String updatedAt,
          }) =>
              NotesCompanion.insert(
            id: id,
            entityId: entityId,
            subjectId: subjectId,
            turnId: turnId,
            civId: civId,
            title: title,
            content: content,
            pinned: pinned,
            noteType: noteType,
            createdAt: createdAt,
            updatedAt: updatedAt,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$NotesTableProcessedTableManager = ProcessedTableManager<
    _$AurelmDatabase,
    $NotesTable,
    NoteRow,
    $$NotesTableFilterComposer,
    $$NotesTableOrderingComposer,
    $$NotesTableAnnotationComposer,
    $$NotesTableCreateCompanionBuilder,
    $$NotesTableUpdateCompanionBuilder,
    (NoteRow, BaseReferences<_$AurelmDatabase, $NotesTable, NoteRow>),
    NoteRow,
    PrefetchHooks Function()>;
typedef $$MapMapsTableCreateCompanionBuilder = MapMapsCompanion Function({
  Value<int> id,
  required String name,
  Value<String?> imagePath,
  Value<String> gridType,
  Value<int> gridCols,
  Value<int> gridRows,
  Value<int?> parentMapId,
  Value<int?> parentCellQ,
  Value<int?> parentCellR,
  required String createdAt,
});
typedef $$MapMapsTableUpdateCompanionBuilder = MapMapsCompanion Function({
  Value<int> id,
  Value<String> name,
  Value<String?> imagePath,
  Value<String> gridType,
  Value<int> gridCols,
  Value<int> gridRows,
  Value<int?> parentMapId,
  Value<int?> parentCellQ,
  Value<int?> parentCellR,
  Value<String> createdAt,
});

class $$MapMapsTableFilterComposer
    extends Composer<_$AurelmDatabase, $MapMapsTable> {
  $$MapMapsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get name => $composableBuilder(
      column: $table.name, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get imagePath => $composableBuilder(
      column: $table.imagePath, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get gridType => $composableBuilder(
      column: $table.gridType, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get gridCols => $composableBuilder(
      column: $table.gridCols, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get gridRows => $composableBuilder(
      column: $table.gridRows, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get parentMapId => $composableBuilder(
      column: $table.parentMapId, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get parentCellQ => $composableBuilder(
      column: $table.parentCellQ, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get parentCellR => $composableBuilder(
      column: $table.parentCellR, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnFilters(column));
}

class $$MapMapsTableOrderingComposer
    extends Composer<_$AurelmDatabase, $MapMapsTable> {
  $$MapMapsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get name => $composableBuilder(
      column: $table.name, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get imagePath => $composableBuilder(
      column: $table.imagePath, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get gridType => $composableBuilder(
      column: $table.gridType, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get gridCols => $composableBuilder(
      column: $table.gridCols, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get gridRows => $composableBuilder(
      column: $table.gridRows, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get parentMapId => $composableBuilder(
      column: $table.parentMapId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get parentCellQ => $composableBuilder(
      column: $table.parentCellQ, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get parentCellR => $composableBuilder(
      column: $table.parentCellR, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnOrderings(column));
}

class $$MapMapsTableAnnotationComposer
    extends Composer<_$AurelmDatabase, $MapMapsTable> {
  $$MapMapsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get name =>
      $composableBuilder(column: $table.name, builder: (column) => column);

  GeneratedColumn<String> get imagePath =>
      $composableBuilder(column: $table.imagePath, builder: (column) => column);

  GeneratedColumn<String> get gridType =>
      $composableBuilder(column: $table.gridType, builder: (column) => column);

  GeneratedColumn<int> get gridCols =>
      $composableBuilder(column: $table.gridCols, builder: (column) => column);

  GeneratedColumn<int> get gridRows =>
      $composableBuilder(column: $table.gridRows, builder: (column) => column);

  GeneratedColumn<int> get parentMapId => $composableBuilder(
      column: $table.parentMapId, builder: (column) => column);

  GeneratedColumn<int> get parentCellQ => $composableBuilder(
      column: $table.parentCellQ, builder: (column) => column);

  GeneratedColumn<int> get parentCellR => $composableBuilder(
      column: $table.parentCellR, builder: (column) => column);

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);
}

class $$MapMapsTableTableManager extends RootTableManager<
    _$AurelmDatabase,
    $MapMapsTable,
    MapRow,
    $$MapMapsTableFilterComposer,
    $$MapMapsTableOrderingComposer,
    $$MapMapsTableAnnotationComposer,
    $$MapMapsTableCreateCompanionBuilder,
    $$MapMapsTableUpdateCompanionBuilder,
    (MapRow, BaseReferences<_$AurelmDatabase, $MapMapsTable, MapRow>),
    MapRow,
    PrefetchHooks Function()> {
  $$MapMapsTableTableManager(_$AurelmDatabase db, $MapMapsTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$MapMapsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$MapMapsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$MapMapsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<int> id = const Value.absent(),
            Value<String> name = const Value.absent(),
            Value<String?> imagePath = const Value.absent(),
            Value<String> gridType = const Value.absent(),
            Value<int> gridCols = const Value.absent(),
            Value<int> gridRows = const Value.absent(),
            Value<int?> parentMapId = const Value.absent(),
            Value<int?> parentCellQ = const Value.absent(),
            Value<int?> parentCellR = const Value.absent(),
            Value<String> createdAt = const Value.absent(),
          }) =>
              MapMapsCompanion(
            id: id,
            name: name,
            imagePath: imagePath,
            gridType: gridType,
            gridCols: gridCols,
            gridRows: gridRows,
            parentMapId: parentMapId,
            parentCellQ: parentCellQ,
            parentCellR: parentCellR,
            createdAt: createdAt,
          ),
          createCompanionCallback: ({
            Value<int> id = const Value.absent(),
            required String name,
            Value<String?> imagePath = const Value.absent(),
            Value<String> gridType = const Value.absent(),
            Value<int> gridCols = const Value.absent(),
            Value<int> gridRows = const Value.absent(),
            Value<int?> parentMapId = const Value.absent(),
            Value<int?> parentCellQ = const Value.absent(),
            Value<int?> parentCellR = const Value.absent(),
            required String createdAt,
          }) =>
              MapMapsCompanion.insert(
            id: id,
            name: name,
            imagePath: imagePath,
            gridType: gridType,
            gridCols: gridCols,
            gridRows: gridRows,
            parentMapId: parentMapId,
            parentCellQ: parentCellQ,
            parentCellR: parentCellR,
            createdAt: createdAt,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$MapMapsTableProcessedTableManager = ProcessedTableManager<
    _$AurelmDatabase,
    $MapMapsTable,
    MapRow,
    $$MapMapsTableFilterComposer,
    $$MapMapsTableOrderingComposer,
    $$MapMapsTableAnnotationComposer,
    $$MapMapsTableCreateCompanionBuilder,
    $$MapMapsTableUpdateCompanionBuilder,
    (MapRow, BaseReferences<_$AurelmDatabase, $MapMapsTable, MapRow>),
    MapRow,
    PrefetchHooks Function()>;
typedef $$MapCellsTableCreateCompanionBuilder = MapCellsCompanion Function({
  required int mapId,
  required int q,
  required int r,
  Value<String> terrainType,
  Value<int?> controllingCivId,
  Value<int?> entityId,
  Value<String?> label,
  Value<int?> childMapId,
  Value<String?> metadata,
  Value<int> rowid,
});
typedef $$MapCellsTableUpdateCompanionBuilder = MapCellsCompanion Function({
  Value<int> mapId,
  Value<int> q,
  Value<int> r,
  Value<String> terrainType,
  Value<int?> controllingCivId,
  Value<int?> entityId,
  Value<String?> label,
  Value<int?> childMapId,
  Value<String?> metadata,
  Value<int> rowid,
});

class $$MapCellsTableFilterComposer
    extends Composer<_$AurelmDatabase, $MapCellsTable> {
  $$MapCellsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get mapId => $composableBuilder(
      column: $table.mapId, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get q => $composableBuilder(
      column: $table.q, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get r => $composableBuilder(
      column: $table.r, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get terrainType => $composableBuilder(
      column: $table.terrainType, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get controllingCivId => $composableBuilder(
      column: $table.controllingCivId,
      builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get entityId => $composableBuilder(
      column: $table.entityId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get label => $composableBuilder(
      column: $table.label, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get childMapId => $composableBuilder(
      column: $table.childMapId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get metadata => $composableBuilder(
      column: $table.metadata, builder: (column) => ColumnFilters(column));
}

class $$MapCellsTableOrderingComposer
    extends Composer<_$AurelmDatabase, $MapCellsTable> {
  $$MapCellsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get mapId => $composableBuilder(
      column: $table.mapId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get q => $composableBuilder(
      column: $table.q, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get r => $composableBuilder(
      column: $table.r, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get terrainType => $composableBuilder(
      column: $table.terrainType, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get controllingCivId => $composableBuilder(
      column: $table.controllingCivId,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get entityId => $composableBuilder(
      column: $table.entityId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get label => $composableBuilder(
      column: $table.label, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get childMapId => $composableBuilder(
      column: $table.childMapId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get metadata => $composableBuilder(
      column: $table.metadata, builder: (column) => ColumnOrderings(column));
}

class $$MapCellsTableAnnotationComposer
    extends Composer<_$AurelmDatabase, $MapCellsTable> {
  $$MapCellsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get mapId =>
      $composableBuilder(column: $table.mapId, builder: (column) => column);

  GeneratedColumn<int> get q =>
      $composableBuilder(column: $table.q, builder: (column) => column);

  GeneratedColumn<int> get r =>
      $composableBuilder(column: $table.r, builder: (column) => column);

  GeneratedColumn<String> get terrainType => $composableBuilder(
      column: $table.terrainType, builder: (column) => column);

  GeneratedColumn<int> get controllingCivId => $composableBuilder(
      column: $table.controllingCivId, builder: (column) => column);

  GeneratedColumn<int> get entityId =>
      $composableBuilder(column: $table.entityId, builder: (column) => column);

  GeneratedColumn<String> get label =>
      $composableBuilder(column: $table.label, builder: (column) => column);

  GeneratedColumn<int> get childMapId => $composableBuilder(
      column: $table.childMapId, builder: (column) => column);

  GeneratedColumn<String> get metadata =>
      $composableBuilder(column: $table.metadata, builder: (column) => column);
}

class $$MapCellsTableTableManager extends RootTableManager<
    _$AurelmDatabase,
    $MapCellsTable,
    MapCellRow,
    $$MapCellsTableFilterComposer,
    $$MapCellsTableOrderingComposer,
    $$MapCellsTableAnnotationComposer,
    $$MapCellsTableCreateCompanionBuilder,
    $$MapCellsTableUpdateCompanionBuilder,
    (MapCellRow, BaseReferences<_$AurelmDatabase, $MapCellsTable, MapCellRow>),
    MapCellRow,
    PrefetchHooks Function()> {
  $$MapCellsTableTableManager(_$AurelmDatabase db, $MapCellsTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$MapCellsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$MapCellsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$MapCellsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<int> mapId = const Value.absent(),
            Value<int> q = const Value.absent(),
            Value<int> r = const Value.absent(),
            Value<String> terrainType = const Value.absent(),
            Value<int?> controllingCivId = const Value.absent(),
            Value<int?> entityId = const Value.absent(),
            Value<String?> label = const Value.absent(),
            Value<int?> childMapId = const Value.absent(),
            Value<String?> metadata = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              MapCellsCompanion(
            mapId: mapId,
            q: q,
            r: r,
            terrainType: terrainType,
            controllingCivId: controllingCivId,
            entityId: entityId,
            label: label,
            childMapId: childMapId,
            metadata: metadata,
            rowid: rowid,
          ),
          createCompanionCallback: ({
            required int mapId,
            required int q,
            required int r,
            Value<String> terrainType = const Value.absent(),
            Value<int?> controllingCivId = const Value.absent(),
            Value<int?> entityId = const Value.absent(),
            Value<String?> label = const Value.absent(),
            Value<int?> childMapId = const Value.absent(),
            Value<String?> metadata = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              MapCellsCompanion.insert(
            mapId: mapId,
            q: q,
            r: r,
            terrainType: terrainType,
            controllingCivId: controllingCivId,
            entityId: entityId,
            label: label,
            childMapId: childMapId,
            metadata: metadata,
            rowid: rowid,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$MapCellsTableProcessedTableManager = ProcessedTableManager<
    _$AurelmDatabase,
    $MapCellsTable,
    MapCellRow,
    $$MapCellsTableFilterComposer,
    $$MapCellsTableOrderingComposer,
    $$MapCellsTableAnnotationComposer,
    $$MapCellsTableCreateCompanionBuilder,
    $$MapCellsTableUpdateCompanionBuilder,
    (MapCellRow, BaseReferences<_$AurelmDatabase, $MapCellsTable, MapCellRow>),
    MapCellRow,
    PrefetchHooks Function()>;
typedef $$MapCellEventsTableCreateCompanionBuilder = MapCellEventsCompanion
    Function({
  Value<int> id,
  required int mapId,
  required int q,
  required int r,
  Value<int?> turnId,
  required String description,
  Value<String> eventType,
  required String createdAt,
});
typedef $$MapCellEventsTableUpdateCompanionBuilder = MapCellEventsCompanion
    Function({
  Value<int> id,
  Value<int> mapId,
  Value<int> q,
  Value<int> r,
  Value<int?> turnId,
  Value<String> description,
  Value<String> eventType,
  Value<String> createdAt,
});

class $$MapCellEventsTableFilterComposer
    extends Composer<_$AurelmDatabase, $MapCellEventsTable> {
  $$MapCellEventsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get mapId => $composableBuilder(
      column: $table.mapId, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get q => $composableBuilder(
      column: $table.q, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get r => $composableBuilder(
      column: $table.r, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get turnId => $composableBuilder(
      column: $table.turnId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get eventType => $composableBuilder(
      column: $table.eventType, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnFilters(column));
}

class $$MapCellEventsTableOrderingComposer
    extends Composer<_$AurelmDatabase, $MapCellEventsTable> {
  $$MapCellEventsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get mapId => $composableBuilder(
      column: $table.mapId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get q => $composableBuilder(
      column: $table.q, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get r => $composableBuilder(
      column: $table.r, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get turnId => $composableBuilder(
      column: $table.turnId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get eventType => $composableBuilder(
      column: $table.eventType, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnOrderings(column));
}

class $$MapCellEventsTableAnnotationComposer
    extends Composer<_$AurelmDatabase, $MapCellEventsTable> {
  $$MapCellEventsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get mapId =>
      $composableBuilder(column: $table.mapId, builder: (column) => column);

  GeneratedColumn<int> get q =>
      $composableBuilder(column: $table.q, builder: (column) => column);

  GeneratedColumn<int> get r =>
      $composableBuilder(column: $table.r, builder: (column) => column);

  GeneratedColumn<int> get turnId =>
      $composableBuilder(column: $table.turnId, builder: (column) => column);

  GeneratedColumn<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => column);

  GeneratedColumn<String> get eventType =>
      $composableBuilder(column: $table.eventType, builder: (column) => column);

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);
}

class $$MapCellEventsTableTableManager extends RootTableManager<
    _$AurelmDatabase,
    $MapCellEventsTable,
    MapCellEventRow,
    $$MapCellEventsTableFilterComposer,
    $$MapCellEventsTableOrderingComposer,
    $$MapCellEventsTableAnnotationComposer,
    $$MapCellEventsTableCreateCompanionBuilder,
    $$MapCellEventsTableUpdateCompanionBuilder,
    (
      MapCellEventRow,
      BaseReferences<_$AurelmDatabase, $MapCellEventsTable, MapCellEventRow>
    ),
    MapCellEventRow,
    PrefetchHooks Function()> {
  $$MapCellEventsTableTableManager(
      _$AurelmDatabase db, $MapCellEventsTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$MapCellEventsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$MapCellEventsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$MapCellEventsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<int> id = const Value.absent(),
            Value<int> mapId = const Value.absent(),
            Value<int> q = const Value.absent(),
            Value<int> r = const Value.absent(),
            Value<int?> turnId = const Value.absent(),
            Value<String> description = const Value.absent(),
            Value<String> eventType = const Value.absent(),
            Value<String> createdAt = const Value.absent(),
          }) =>
              MapCellEventsCompanion(
            id: id,
            mapId: mapId,
            q: q,
            r: r,
            turnId: turnId,
            description: description,
            eventType: eventType,
            createdAt: createdAt,
          ),
          createCompanionCallback: ({
            Value<int> id = const Value.absent(),
            required int mapId,
            required int q,
            required int r,
            Value<int?> turnId = const Value.absent(),
            required String description,
            Value<String> eventType = const Value.absent(),
            required String createdAt,
          }) =>
              MapCellEventsCompanion.insert(
            id: id,
            mapId: mapId,
            q: q,
            r: r,
            turnId: turnId,
            description: description,
            eventType: eventType,
            createdAt: createdAt,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$MapCellEventsTableProcessedTableManager = ProcessedTableManager<
    _$AurelmDatabase,
    $MapCellEventsTable,
    MapCellEventRow,
    $$MapCellEventsTableFilterComposer,
    $$MapCellEventsTableOrderingComposer,
    $$MapCellEventsTableAnnotationComposer,
    $$MapCellEventsTableCreateCompanionBuilder,
    $$MapCellEventsTableUpdateCompanionBuilder,
    (
      MapCellEventRow,
      BaseReferences<_$AurelmDatabase, $MapCellEventsTable, MapCellEventRow>
    ),
    MapCellEventRow,
    PrefetchHooks Function()>;

class $AurelmDatabaseManager {
  final _$AurelmDatabase _db;
  $AurelmDatabaseManager(this._db);
  $$CivCivilizationsTableTableManager get civCivilizations =>
      $$CivCivilizationsTableTableManager(_db, _db.civCivilizations);
  $$TurnTurnsTableTableManager get turnTurns =>
      $$TurnTurnsTableTableManager(_db, _db.turnTurns);
  $$TurnSegmentsTableTableManager get turnSegments =>
      $$TurnSegmentsTableTableManager(_db, _db.turnSegments);
  $$EntityEntitiesTableTableManager get entityEntities =>
      $$EntityEntitiesTableTableManager(_db, _db.entityEntities);
  $$EntityAliasesTableTableManager get entityAliases =>
      $$EntityAliasesTableTableManager(_db, _db.entityAliases);
  $$EntityMentionsTableTableManager get entityMentions =>
      $$EntityMentionsTableTableManager(_db, _db.entityMentions);
  $$EntityRelationsTableTableManager get entityRelations =>
      $$EntityRelationsTableTableManager(_db, _db.entityRelations);
  $$PipelineRunsTableTableManager get pipelineRuns =>
      $$PipelineRunsTableTableManager(_db, _db.pipelineRuns);
  $$SubjectSubjectsTableTableManager get subjectSubjects =>
      $$SubjectSubjectsTableTableManager(_db, _db.subjectSubjects);
  $$SubjectOptionsTableTableManager get subjectOptions =>
      $$SubjectOptionsTableTableManager(_db, _db.subjectOptions);
  $$SubjectResolutionsTableTableManager get subjectResolutions =>
      $$SubjectResolutionsTableTableManager(_db, _db.subjectResolutions);
  $$NotesTableTableManager get notes =>
      $$NotesTableTableManager(_db, _db.notes);
  $$MapMapsTableTableManager get mapMaps =>
      $$MapMapsTableTableManager(_db, _db.mapMaps);
  $$MapCellsTableTableManager get mapCells =>
      $$MapCellsTableTableManager(_db, _db.mapCells);
  $$MapCellEventsTableTableManager get mapCellEvents =>
      $$MapCellEventsTableTableManager(_db, _db.mapCellEvents);
}
