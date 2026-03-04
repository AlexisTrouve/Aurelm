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
  @override
  List<GeneratedColumn> get $columns => [
        id,
        civId,
        turnNumber,
        title,
        summary,
        rawMessageIds,
        turnType,
        gameDateStart,
        gameDateEnd,
        createdAt,
        processedAt
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
  final String rawMessageIds;
  final String turnType;
  final String? gameDateStart;
  final String? gameDateEnd;
  final String createdAt;
  final String? processedAt;
  const TurnRow(
      {required this.id,
      required this.civId,
      required this.turnNumber,
      this.title,
      this.summary,
      required this.rawMessageIds,
      required this.turnType,
      this.gameDateStart,
      this.gameDateEnd,
      required this.createdAt,
      this.processedAt});
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
      rawMessageIds: serializer.fromJson<String>(json['rawMessageIds']),
      turnType: serializer.fromJson<String>(json['turnType']),
      gameDateStart: serializer.fromJson<String?>(json['gameDateStart']),
      gameDateEnd: serializer.fromJson<String?>(json['gameDateEnd']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
      processedAt: serializer.fromJson<String?>(json['processedAt']),
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
      'rawMessageIds': serializer.toJson<String>(rawMessageIds),
      'turnType': serializer.toJson<String>(turnType),
      'gameDateStart': serializer.toJson<String?>(gameDateStart),
      'gameDateEnd': serializer.toJson<String?>(gameDateEnd),
      'createdAt': serializer.toJson<String>(createdAt),
      'processedAt': serializer.toJson<String?>(processedAt),
    };
  }

  TurnRow copyWith(
          {int? id,
          int? civId,
          int? turnNumber,
          Value<String?> title = const Value.absent(),
          Value<String?> summary = const Value.absent(),
          String? rawMessageIds,
          String? turnType,
          Value<String?> gameDateStart = const Value.absent(),
          Value<String?> gameDateEnd = const Value.absent(),
          String? createdAt,
          Value<String?> processedAt = const Value.absent()}) =>
      TurnRow(
        id: id ?? this.id,
        civId: civId ?? this.civId,
        turnNumber: turnNumber ?? this.turnNumber,
        title: title.present ? title.value : this.title,
        summary: summary.present ? summary.value : this.summary,
        rawMessageIds: rawMessageIds ?? this.rawMessageIds,
        turnType: turnType ?? this.turnType,
        gameDateStart:
            gameDateStart.present ? gameDateStart.value : this.gameDateStart,
        gameDateEnd: gameDateEnd.present ? gameDateEnd.value : this.gameDateEnd,
        createdAt: createdAt ?? this.createdAt,
        processedAt: processedAt.present ? processedAt.value : this.processedAt,
      );
  TurnRow copyWithCompanion(TurnTurnsCompanion data) {
    return TurnRow(
      id: data.id.present ? data.id.value : this.id,
      civId: data.civId.present ? data.civId.value : this.civId,
      turnNumber:
          data.turnNumber.present ? data.turnNumber.value : this.turnNumber,
      title: data.title.present ? data.title.value : this.title,
      summary: data.summary.present ? data.summary.value : this.summary,
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
          ..write('rawMessageIds: $rawMessageIds, ')
          ..write('turnType: $turnType, ')
          ..write('gameDateStart: $gameDateStart, ')
          ..write('gameDateEnd: $gameDateEnd, ')
          ..write('createdAt: $createdAt, ')
          ..write('processedAt: $processedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
      id,
      civId,
      turnNumber,
      title,
      summary,
      rawMessageIds,
      turnType,
      gameDateStart,
      gameDateEnd,
      createdAt,
      processedAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is TurnRow &&
          other.id == this.id &&
          other.civId == this.civId &&
          other.turnNumber == this.turnNumber &&
          other.title == this.title &&
          other.summary == this.summary &&
          other.rawMessageIds == this.rawMessageIds &&
          other.turnType == this.turnType &&
          other.gameDateStart == this.gameDateStart &&
          other.gameDateEnd == this.gameDateEnd &&
          other.createdAt == this.createdAt &&
          other.processedAt == this.processedAt);
}

class TurnTurnsCompanion extends UpdateCompanion<TurnRow> {
  final Value<int> id;
  final Value<int> civId;
  final Value<int> turnNumber;
  final Value<String?> title;
  final Value<String?> summary;
  final Value<String> rawMessageIds;
  final Value<String> turnType;
  final Value<String?> gameDateStart;
  final Value<String?> gameDateEnd;
  final Value<String> createdAt;
  final Value<String?> processedAt;
  const TurnTurnsCompanion({
    this.id = const Value.absent(),
    this.civId = const Value.absent(),
    this.turnNumber = const Value.absent(),
    this.title = const Value.absent(),
    this.summary = const Value.absent(),
    this.rawMessageIds = const Value.absent(),
    this.turnType = const Value.absent(),
    this.gameDateStart = const Value.absent(),
    this.gameDateEnd = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.processedAt = const Value.absent(),
  });
  TurnTurnsCompanion.insert({
    this.id = const Value.absent(),
    required int civId,
    required int turnNumber,
    this.title = const Value.absent(),
    this.summary = const Value.absent(),
    required String rawMessageIds,
    this.turnType = const Value.absent(),
    this.gameDateStart = const Value.absent(),
    this.gameDateEnd = const Value.absent(),
    required String createdAt,
    this.processedAt = const Value.absent(),
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
    Expression<String>? rawMessageIds,
    Expression<String>? turnType,
    Expression<String>? gameDateStart,
    Expression<String>? gameDateEnd,
    Expression<String>? createdAt,
    Expression<String>? processedAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (civId != null) 'civ_id': civId,
      if (turnNumber != null) 'turn_number': turnNumber,
      if (title != null) 'title': title,
      if (summary != null) 'summary': summary,
      if (rawMessageIds != null) 'raw_message_ids': rawMessageIds,
      if (turnType != null) 'turn_type': turnType,
      if (gameDateStart != null) 'game_date_start': gameDateStart,
      if (gameDateEnd != null) 'game_date_end': gameDateEnd,
      if (createdAt != null) 'created_at': createdAt,
      if (processedAt != null) 'processed_at': processedAt,
    });
  }

  TurnTurnsCompanion copyWith(
      {Value<int>? id,
      Value<int>? civId,
      Value<int>? turnNumber,
      Value<String?>? title,
      Value<String?>? summary,
      Value<String>? rawMessageIds,
      Value<String>? turnType,
      Value<String?>? gameDateStart,
      Value<String?>? gameDateEnd,
      Value<String>? createdAt,
      Value<String?>? processedAt}) {
    return TurnTurnsCompanion(
      id: id ?? this.id,
      civId: civId ?? this.civId,
      turnNumber: turnNumber ?? this.turnNumber,
      title: title ?? this.title,
      summary: summary ?? this.summary,
      rawMessageIds: rawMessageIds ?? this.rawMessageIds,
      turnType: turnType ?? this.turnType,
      gameDateStart: gameDateStart ?? this.gameDateStart,
      gameDateEnd: gameDateEnd ?? this.gameDateEnd,
      createdAt: createdAt ?? this.createdAt,
      processedAt: processedAt ?? this.processedAt,
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
          ..write('rawMessageIds: $rawMessageIds, ')
          ..write('turnType: $turnType, ')
          ..write('gameDateStart: $gameDateStart, ')
          ..write('gameDateEnd: $gameDateEnd, ')
          ..write('createdAt: $createdAt, ')
          ..write('processedAt: $processedAt')
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
  @override
  List<GeneratedColumn> get $columns =>
      [id, turnId, segmentOrder, segmentType, content];
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
  const SegmentRow(
      {required this.id,
      required this.turnId,
      required this.segmentOrder,
      required this.segmentType,
      required this.content});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['turn_id'] = Variable<int>(turnId);
    map['segment_order'] = Variable<int>(segmentOrder);
    map['segment_type'] = Variable<String>(segmentType);
    map['content'] = Variable<String>(content);
    return map;
  }

  TurnSegmentsCompanion toCompanion(bool nullToAbsent) {
    return TurnSegmentsCompanion(
      id: Value(id),
      turnId: Value(turnId),
      segmentOrder: Value(segmentOrder),
      segmentType: Value(segmentType),
      content: Value(content),
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
    };
  }

  SegmentRow copyWith(
          {int? id,
          int? turnId,
          int? segmentOrder,
          String? segmentType,
          String? content}) =>
      SegmentRow(
        id: id ?? this.id,
        turnId: turnId ?? this.turnId,
        segmentOrder: segmentOrder ?? this.segmentOrder,
        segmentType: segmentType ?? this.segmentType,
        content: content ?? this.content,
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
    );
  }

  @override
  String toString() {
    return (StringBuffer('SegmentRow(')
          ..write('id: $id, ')
          ..write('turnId: $turnId, ')
          ..write('segmentOrder: $segmentOrder, ')
          ..write('segmentType: $segmentType, ')
          ..write('content: $content')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode =>
      Object.hash(id, turnId, segmentOrder, segmentType, content);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is SegmentRow &&
          other.id == this.id &&
          other.turnId == this.turnId &&
          other.segmentOrder == this.segmentOrder &&
          other.segmentType == this.segmentType &&
          other.content == this.content);
}

class TurnSegmentsCompanion extends UpdateCompanion<SegmentRow> {
  final Value<int> id;
  final Value<int> turnId;
  final Value<int> segmentOrder;
  final Value<String> segmentType;
  final Value<String> content;
  const TurnSegmentsCompanion({
    this.id = const Value.absent(),
    this.turnId = const Value.absent(),
    this.segmentOrder = const Value.absent(),
    this.segmentType = const Value.absent(),
    this.content = const Value.absent(),
  });
  TurnSegmentsCompanion.insert({
    this.id = const Value.absent(),
    required int turnId,
    required int segmentOrder,
    required String segmentType,
    required String content,
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
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (turnId != null) 'turn_id': turnId,
      if (segmentOrder != null) 'segment_order': segmentOrder,
      if (segmentType != null) 'segment_type': segmentType,
      if (content != null) 'content': content,
    });
  }

  TurnSegmentsCompanion copyWith(
      {Value<int>? id,
      Value<int>? turnId,
      Value<int>? segmentOrder,
      Value<String>? segmentType,
      Value<String>? content}) {
    return TurnSegmentsCompanion(
      id: id ?? this.id,
      turnId: turnId ?? this.turnId,
      segmentOrder: segmentOrder ?? this.segmentOrder,
      segmentType: segmentType ?? this.segmentType,
      content: content ?? this.content,
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
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('TurnSegmentsCompanion(')
          ..write('id: $id, ')
          ..write('turnId: $turnId, ')
          ..write('segmentOrder: $segmentOrder, ')
          ..write('segmentType: $segmentType, ')
          ..write('content: $content')
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
        updatedAt
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
      required this.updatedAt});
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
          String? updatedAt}) =>
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
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, canonicalName, entityType, civId,
      description, firstSeenTurn, lastSeenTurn, isActive, createdAt, updatedAt);
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
          other.updatedAt == this.updatedAt);
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
      Value<String>? updatedAt}) {
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
          ..write('updatedAt: $updatedAt')
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
  @override
  List<GeneratedColumn> get $columns => [id, entityId, alias];
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
  const AliasRow(
      {required this.id, required this.entityId, required this.alias});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['entity_id'] = Variable<int>(entityId);
    map['alias'] = Variable<String>(alias);
    return map;
  }

  EntityAliasesCompanion toCompanion(bool nullToAbsent) {
    return EntityAliasesCompanion(
      id: Value(id),
      entityId: Value(entityId),
      alias: Value(alias),
    );
  }

  factory AliasRow.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return AliasRow(
      id: serializer.fromJson<int>(json['id']),
      entityId: serializer.fromJson<int>(json['entityId']),
      alias: serializer.fromJson<String>(json['alias']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'entityId': serializer.toJson<int>(entityId),
      'alias': serializer.toJson<String>(alias),
    };
  }

  AliasRow copyWith({int? id, int? entityId, String? alias}) => AliasRow(
        id: id ?? this.id,
        entityId: entityId ?? this.entityId,
        alias: alias ?? this.alias,
      );
  AliasRow copyWithCompanion(EntityAliasesCompanion data) {
    return AliasRow(
      id: data.id.present ? data.id.value : this.id,
      entityId: data.entityId.present ? data.entityId.value : this.entityId,
      alias: data.alias.present ? data.alias.value : this.alias,
    );
  }

  @override
  String toString() {
    return (StringBuffer('AliasRow(')
          ..write('id: $id, ')
          ..write('entityId: $entityId, ')
          ..write('alias: $alias')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, entityId, alias);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is AliasRow &&
          other.id == this.id &&
          other.entityId == this.entityId &&
          other.alias == this.alias);
}

class EntityAliasesCompanion extends UpdateCompanion<AliasRow> {
  final Value<int> id;
  final Value<int> entityId;
  final Value<String> alias;
  const EntityAliasesCompanion({
    this.id = const Value.absent(),
    this.entityId = const Value.absent(),
    this.alias = const Value.absent(),
  });
  EntityAliasesCompanion.insert({
    this.id = const Value.absent(),
    required int entityId,
    required String alias,
  })  : entityId = Value(entityId),
        alias = Value(alias);
  static Insertable<AliasRow> custom({
    Expression<int>? id,
    Expression<int>? entityId,
    Expression<String>? alias,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (entityId != null) 'entity_id': entityId,
      if (alias != null) 'alias': alias,
    });
  }

  EntityAliasesCompanion copyWith(
      {Value<int>? id, Value<int>? entityId, Value<String>? alias}) {
    return EntityAliasesCompanion(
      id: id ?? this.id,
      entityId: entityId ?? this.entityId,
      alias: alias ?? this.alias,
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
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('EntityAliasesCompanion(')
          ..write('id: $id, ')
          ..write('entityId: $entityId, ')
          ..write('alias: $alias')
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
  @override
  List<GeneratedColumn> get $columns =>
      [id, entityId, turnId, segmentId, mentionText, context];
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
  const MentionRow(
      {required this.id,
      required this.entityId,
      required this.turnId,
      this.segmentId,
      required this.mentionText,
      this.context});
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
    };
  }

  MentionRow copyWith(
          {int? id,
          int? entityId,
          int? turnId,
          Value<int?> segmentId = const Value.absent(),
          String? mentionText,
          Value<String?> context = const Value.absent()}) =>
      MentionRow(
        id: id ?? this.id,
        entityId: entityId ?? this.entityId,
        turnId: turnId ?? this.turnId,
        segmentId: segmentId.present ? segmentId.value : this.segmentId,
        mentionText: mentionText ?? this.mentionText,
        context: context.present ? context.value : this.context,
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
          ..write('context: $context')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode =>
      Object.hash(id, entityId, turnId, segmentId, mentionText, context);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is MentionRow &&
          other.id == this.id &&
          other.entityId == this.entityId &&
          other.turnId == this.turnId &&
          other.segmentId == this.segmentId &&
          other.mentionText == this.mentionText &&
          other.context == this.context);
}

class EntityMentionsCompanion extends UpdateCompanion<MentionRow> {
  final Value<int> id;
  final Value<int> entityId;
  final Value<int> turnId;
  final Value<int?> segmentId;
  final Value<String> mentionText;
  final Value<String?> context;
  const EntityMentionsCompanion({
    this.id = const Value.absent(),
    this.entityId = const Value.absent(),
    this.turnId = const Value.absent(),
    this.segmentId = const Value.absent(),
    this.mentionText = const Value.absent(),
    this.context = const Value.absent(),
  });
  EntityMentionsCompanion.insert({
    this.id = const Value.absent(),
    required int entityId,
    required int turnId,
    this.segmentId = const Value.absent(),
    required String mentionText,
    this.context = const Value.absent(),
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
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (entityId != null) 'entity_id': entityId,
      if (turnId != null) 'turn_id': turnId,
      if (segmentId != null) 'segment_id': segmentId,
      if (mentionText != null) 'mention_text': mentionText,
      if (context != null) 'context': context,
    });
  }

  EntityMentionsCompanion copyWith(
      {Value<int>? id,
      Value<int>? entityId,
      Value<int>? turnId,
      Value<int?>? segmentId,
      Value<String>? mentionText,
      Value<String?>? context}) {
    return EntityMentionsCompanion(
      id: id ?? this.id,
      entityId: entityId ?? this.entityId,
      turnId: turnId ?? this.turnId,
      segmentId: segmentId ?? this.segmentId,
      mentionText: mentionText ?? this.mentionText,
      context: context ?? this.context,
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
          ..write('context: $context')
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
      'source_turn_id', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
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
        category,
        status,
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
    } else if (isInserting) {
      context.missing(_sourceTurnIdMeta);
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
          .read(DriftSqlType.int, data['${effectivePrefix}source_turn_id'])!,
      direction: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}direction'])!,
      title: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}title'])!,
      description: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}description']),
      category: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}category'])!,
      status: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}status'])!,
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
  final int sourceTurnId;

  /// 'mj_to_pj' = GM poses a choice; 'pj_to_mj' = player takes an initiative
  final String direction;
  final String title;
  final String? description;

  /// 'choice' | 'question' | 'initiative' | 'request'
  final String category;

  /// 'open' | 'resolved' | 'superseded' | 'abandoned'
  final String status;
  final String createdAt;
  final String updatedAt;
  const SubjectRow(
      {required this.id,
      required this.civId,
      required this.sourceTurnId,
      required this.direction,
      required this.title,
      this.description,
      required this.category,
      required this.status,
      required this.createdAt,
      required this.updatedAt});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['civ_id'] = Variable<int>(civId);
    map['source_turn_id'] = Variable<int>(sourceTurnId);
    map['direction'] = Variable<String>(direction);
    map['title'] = Variable<String>(title);
    if (!nullToAbsent || description != null) {
      map['description'] = Variable<String>(description);
    }
    map['category'] = Variable<String>(category);
    map['status'] = Variable<String>(status);
    map['created_at'] = Variable<String>(createdAt);
    map['updated_at'] = Variable<String>(updatedAt);
    return map;
  }

  SubjectSubjectsCompanion toCompanion(bool nullToAbsent) {
    return SubjectSubjectsCompanion(
      id: Value(id),
      civId: Value(civId),
      sourceTurnId: Value(sourceTurnId),
      direction: Value(direction),
      title: Value(title),
      description: description == null && nullToAbsent
          ? const Value.absent()
          : Value(description),
      category: Value(category),
      status: Value(status),
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
      sourceTurnId: serializer.fromJson<int>(json['sourceTurnId']),
      direction: serializer.fromJson<String>(json['direction']),
      title: serializer.fromJson<String>(json['title']),
      description: serializer.fromJson<String?>(json['description']),
      category: serializer.fromJson<String>(json['category']),
      status: serializer.fromJson<String>(json['status']),
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
      'sourceTurnId': serializer.toJson<int>(sourceTurnId),
      'direction': serializer.toJson<String>(direction),
      'title': serializer.toJson<String>(title),
      'description': serializer.toJson<String?>(description),
      'category': serializer.toJson<String>(category),
      'status': serializer.toJson<String>(status),
      'createdAt': serializer.toJson<String>(createdAt),
      'updatedAt': serializer.toJson<String>(updatedAt),
    };
  }

  SubjectRow copyWith(
          {int? id,
          int? civId,
          int? sourceTurnId,
          String? direction,
          String? title,
          Value<String?> description = const Value.absent(),
          String? category,
          String? status,
          String? createdAt,
          String? updatedAt}) =>
      SubjectRow(
        id: id ?? this.id,
        civId: civId ?? this.civId,
        sourceTurnId: sourceTurnId ?? this.sourceTurnId,
        direction: direction ?? this.direction,
        title: title ?? this.title,
        description: description.present ? description.value : this.description,
        category: category ?? this.category,
        status: status ?? this.status,
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
      category: data.category.present ? data.category.value : this.category,
      status: data.status.present ? data.status.value : this.status,
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
          ..write('category: $category, ')
          ..write('status: $status, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, civId, sourceTurnId, direction, title,
      description, category, status, createdAt, updatedAt);
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
          other.category == this.category &&
          other.status == this.status &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt);
}

class SubjectSubjectsCompanion extends UpdateCompanion<SubjectRow> {
  final Value<int> id;
  final Value<int> civId;
  final Value<int> sourceTurnId;
  final Value<String> direction;
  final Value<String> title;
  final Value<String?> description;
  final Value<String> category;
  final Value<String> status;
  final Value<String> createdAt;
  final Value<String> updatedAt;
  const SubjectSubjectsCompanion({
    this.id = const Value.absent(),
    this.civId = const Value.absent(),
    this.sourceTurnId = const Value.absent(),
    this.direction = const Value.absent(),
    this.title = const Value.absent(),
    this.description = const Value.absent(),
    this.category = const Value.absent(),
    this.status = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
  });
  SubjectSubjectsCompanion.insert({
    this.id = const Value.absent(),
    required int civId,
    required int sourceTurnId,
    required String direction,
    required String title,
    this.description = const Value.absent(),
    required String category,
    this.status = const Value.absent(),
    required String createdAt,
    required String updatedAt,
  })  : civId = Value(civId),
        sourceTurnId = Value(sourceTurnId),
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
    Expression<String>? category,
    Expression<String>? status,
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
      if (category != null) 'category': category,
      if (status != null) 'status': status,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
    });
  }

  SubjectSubjectsCompanion copyWith(
      {Value<int>? id,
      Value<int>? civId,
      Value<int>? sourceTurnId,
      Value<String>? direction,
      Value<String>? title,
      Value<String?>? description,
      Value<String>? category,
      Value<String>? status,
      Value<String>? createdAt,
      Value<String>? updatedAt}) {
    return SubjectSubjectsCompanion(
      id: id ?? this.id,
      civId: civId ?? this.civId,
      sourceTurnId: sourceTurnId ?? this.sourceTurnId,
      direction: direction ?? this.direction,
      title: title ?? this.title,
      description: description ?? this.description,
      category: category ?? this.category,
      status: status ?? this.status,
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
    if (category.present) {
      map['category'] = Variable<String>(category.value);
    }
    if (status.present) {
      map['status'] = Variable<String>(status.value);
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
          ..write('category: $category, ')
          ..write('status: $status, ')
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
          ..write('isLibre: $isLibre, ')
          ..write('confidence: $confidence, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, subjectId, resolvedByTurnId,
      chosenOptionId, resolutionText, isLibre, confidence, createdAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is SubjectResolutionRow &&
          other.id == this.id &&
          other.subjectId == this.subjectId &&
          other.resolvedByTurnId == this.resolvedByTurnId &&
          other.chosenOptionId == this.chosenOptionId &&
          other.resolutionText == this.resolutionText &&
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
  final Value<bool> isLibre;
  final Value<double> confidence;
  final Value<String> createdAt;
  const SubjectResolutionsCompanion({
    this.id = const Value.absent(),
    this.subjectId = const Value.absent(),
    this.resolvedByTurnId = const Value.absent(),
    this.chosenOptionId = const Value.absent(),
    this.resolutionText = const Value.absent(),
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
      Value<bool>? isLibre,
      Value<double>? confidence,
      Value<String>? createdAt}) {
    return SubjectResolutionsCompanion(
      id: id ?? this.id,
      subjectId: subjectId ?? this.subjectId,
      resolvedByTurnId: resolvedByTurnId ?? this.resolvedByTurnId,
      chosenOptionId: chosenOptionId ?? this.chosenOptionId,
      resolutionText: resolutionText ?? this.resolutionText,
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
          ..write('isLibre: $isLibre, ')
          ..write('confidence: $confidence, ')
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
  late final CivilizationDao civilizationDao =
      CivilizationDao(this as AurelmDatabase);
  late final TurnDao turnDao = TurnDao(this as AurelmDatabase);
  late final EntityDao entityDao = EntityDao(this as AurelmDatabase);
  late final RelationDao relationDao = RelationDao(this as AurelmDatabase);
  late final PipelineDao pipelineDao = PipelineDao(this as AurelmDatabase);
  late final SubjectDao subjectDao = SubjectDao(this as AurelmDatabase);
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
        subjectResolutions
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
  required String rawMessageIds,
  Value<String> turnType,
  Value<String?> gameDateStart,
  Value<String?> gameDateEnd,
  required String createdAt,
  Value<String?> processedAt,
});
typedef $$TurnTurnsTableUpdateCompanionBuilder = TurnTurnsCompanion Function({
  Value<int> id,
  Value<int> civId,
  Value<int> turnNumber,
  Value<String?> title,
  Value<String?> summary,
  Value<String> rawMessageIds,
  Value<String> turnType,
  Value<String?> gameDateStart,
  Value<String?> gameDateEnd,
  Value<String> createdAt,
  Value<String?> processedAt,
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
            Value<String> rawMessageIds = const Value.absent(),
            Value<String> turnType = const Value.absent(),
            Value<String?> gameDateStart = const Value.absent(),
            Value<String?> gameDateEnd = const Value.absent(),
            Value<String> createdAt = const Value.absent(),
            Value<String?> processedAt = const Value.absent(),
          }) =>
              TurnTurnsCompanion(
            id: id,
            civId: civId,
            turnNumber: turnNumber,
            title: title,
            summary: summary,
            rawMessageIds: rawMessageIds,
            turnType: turnType,
            gameDateStart: gameDateStart,
            gameDateEnd: gameDateEnd,
            createdAt: createdAt,
            processedAt: processedAt,
          ),
          createCompanionCallback: ({
            Value<int> id = const Value.absent(),
            required int civId,
            required int turnNumber,
            Value<String?> title = const Value.absent(),
            Value<String?> summary = const Value.absent(),
            required String rawMessageIds,
            Value<String> turnType = const Value.absent(),
            Value<String?> gameDateStart = const Value.absent(),
            Value<String?> gameDateEnd = const Value.absent(),
            required String createdAt,
            Value<String?> processedAt = const Value.absent(),
          }) =>
              TurnTurnsCompanion.insert(
            id: id,
            civId: civId,
            turnNumber: turnNumber,
            title: title,
            summary: summary,
            rawMessageIds: rawMessageIds,
            turnType: turnType,
            gameDateStart: gameDateStart,
            gameDateEnd: gameDateEnd,
            createdAt: createdAt,
            processedAt: processedAt,
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
});
typedef $$TurnSegmentsTableUpdateCompanionBuilder = TurnSegmentsCompanion
    Function({
  Value<int> id,
  Value<int> turnId,
  Value<int> segmentOrder,
  Value<String> segmentType,
  Value<String> content,
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
          }) =>
              TurnSegmentsCompanion(
            id: id,
            turnId: turnId,
            segmentOrder: segmentOrder,
            segmentType: segmentType,
            content: content,
          ),
          createCompanionCallback: ({
            Value<int> id = const Value.absent(),
            required int turnId,
            required int segmentOrder,
            required String segmentType,
            required String content,
          }) =>
              TurnSegmentsCompanion.insert(
            id: id,
            turnId: turnId,
            segmentOrder: segmentOrder,
            segmentType: segmentType,
            content: content,
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
});
typedef $$EntityAliasesTableUpdateCompanionBuilder = EntityAliasesCompanion
    Function({
  Value<int> id,
  Value<int> entityId,
  Value<String> alias,
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
          }) =>
              EntityAliasesCompanion(
            id: id,
            entityId: entityId,
            alias: alias,
          ),
          createCompanionCallback: ({
            Value<int> id = const Value.absent(),
            required int entityId,
            required String alias,
          }) =>
              EntityAliasesCompanion.insert(
            id: id,
            entityId: entityId,
            alias: alias,
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
});
typedef $$EntityMentionsTableUpdateCompanionBuilder = EntityMentionsCompanion
    Function({
  Value<int> id,
  Value<int> entityId,
  Value<int> turnId,
  Value<int?> segmentId,
  Value<String> mentionText,
  Value<String?> context,
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
          }) =>
              EntityMentionsCompanion(
            id: id,
            entityId: entityId,
            turnId: turnId,
            segmentId: segmentId,
            mentionText: mentionText,
            context: context,
          ),
          createCompanionCallback: ({
            Value<int> id = const Value.absent(),
            required int entityId,
            required int turnId,
            Value<int?> segmentId = const Value.absent(),
            required String mentionText,
            Value<String?> context = const Value.absent(),
          }) =>
              EntityMentionsCompanion.insert(
            id: id,
            entityId: entityId,
            turnId: turnId,
            segmentId: segmentId,
            mentionText: mentionText,
            context: context,
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
  required int sourceTurnId,
  required String direction,
  required String title,
  Value<String?> description,
  required String category,
  Value<String> status,
  required String createdAt,
  required String updatedAt,
});
typedef $$SubjectSubjectsTableUpdateCompanionBuilder = SubjectSubjectsCompanion
    Function({
  Value<int> id,
  Value<int> civId,
  Value<int> sourceTurnId,
  Value<String> direction,
  Value<String> title,
  Value<String?> description,
  Value<String> category,
  Value<String> status,
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

  ColumnFilters<String> get category => $composableBuilder(
      column: $table.category, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get status => $composableBuilder(
      column: $table.status, builder: (column) => ColumnFilters(column));

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

  ColumnOrderings<String> get category => $composableBuilder(
      column: $table.category, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get status => $composableBuilder(
      column: $table.status, builder: (column) => ColumnOrderings(column));

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

  GeneratedColumn<String> get category =>
      $composableBuilder(column: $table.category, builder: (column) => column);

  GeneratedColumn<String> get status =>
      $composableBuilder(column: $table.status, builder: (column) => column);

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
            Value<int> sourceTurnId = const Value.absent(),
            Value<String> direction = const Value.absent(),
            Value<String> title = const Value.absent(),
            Value<String?> description = const Value.absent(),
            Value<String> category = const Value.absent(),
            Value<String> status = const Value.absent(),
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
            category: category,
            status: status,
            createdAt: createdAt,
            updatedAt: updatedAt,
          ),
          createCompanionCallback: ({
            Value<int> id = const Value.absent(),
            required int civId,
            required int sourceTurnId,
            required String direction,
            required String title,
            Value<String?> description = const Value.absent(),
            required String category,
            Value<String> status = const Value.absent(),
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
            category: category,
            status: status,
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
}
