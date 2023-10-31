from xm_file import XMFile
from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo
import sys

XM_STOP_NOTE = 97
XM_HIGHEST_NOTE = 96
XM_LOWEST_NOTE = 0
XM_TO_MIDI_PITCH = 11
MIDI_HIGHEST_NOTE = 127
MIDI_LOWEST_NOTE = 0

# MIDI F-5 = 77, XM note F-5 = 66
xm_file = XMFile('sample.xm')

print(f'{xm_file.header.n_channels} channels')
print(f'{xm_file.header.n_patterns} distinct patterns')
print(f'{xm_file.header.song_length} patterns in length')
# print(f'Pattern order: {xm_file.header.pattern_order_table[:xm_file.header.song_length]}')

midi_file = MidiFile()
# Create one MIDI track per XM channel
midi_tracks = [MidiTrack() for _ in range(xm_file.header.n_channels)]
midi_file.tracks.extend(midi_tracks)

for track in midi_tracks:
    track.append(MetaMessage('set_tempo', tempo=bpm2tempo(xm_file.header.bpm)))

# Set length
TICKS_PER_SIXTEENTH_NOTE = midi_file.ticks_per_beat // 4

# For each pattern, up to the end of the song
for pattern_index, pattern in enumerate(xm_file.patterns[:xm_file.header.song_length]):
    # For each row in the pattern
    pattern_data = pattern.pattern_data()
    for pattern_row, pattern_row_data in enumerate(pattern_data):
        # The row is expected to have the same number of elements as there are channels
        '''
        if xm_file.header.n_channels != len(pattern_row_data):
            print(f'Row {pattern_row:02X} of pattern {pattern_index:02X} has {len(pattern_row_data)} channels')
            continue
        '''
        # For each note in the row
        for channel, row_note in enumerate(pattern_row_data):
            # Reset note off notification
            note_off_triggered = False
            # If the note is out of range, skip it
            if row_note.note > XM_STOP_NOTE or row_note.note < XM_LOWEST_NOTE:
                if (row_note.note != 0):
                    print(f'Row {pattern_row:02X} of pattern {pattern_index:02X} has note {row_note.note}'
                          , file=sys.stderr)
                continue
            # Turn off the previous note if there is a stop note on this row or if this note is a repeat of a previous one.
            if pattern_row != 0:
                # If the note is the stop note, stop the note before this one
                if row_note.note == XM_STOP_NOTE:
                    midi_tracks[channel].append(
                        Message('note_off'
                                , channel=channel
                                , note=pattern_data[pattern_row - 1][channel].note + XM_TO_MIDI_PITCH
                                , time=TICKS_PER_SIXTEENTH_NOTE))
                else:
                    # Get the last note_on message sent on this channel,
                    # compare the note to this one,
                    # send note_off message if they're the same.
                    message_index = len(midi_tracks[channel]) - 1
                    while (
                        message_index >= 0
                        and type(midi_tracks[channel][message_index]) != Message
                        and midi_tracks[channel][message_index].type != 'note_on'
                    ):
                        message_index -= 1
                    if (
                        message_index >= 0
                        and midi_tracks[channel][message_index].note == row_note.note + XM_TO_MIDI_PITCH
                    ):
                        midi_tracks[channel].append(
                            Message('note_off'
                                , channel=channel
                                , note=midi_tracks[channel][message_index].note
                                , time=TICKS_PER_SIXTEENTH_NOTE))
                        note_off_triggered = True
            # Note is not the same as the last note,
            # and is the null note
            if row_note.note == XM_LOWEST_NOTE:
                # Extend the previous note's length by a sixteenth note
                midi_tracks[channel][-1].time += TICKS_PER_SIXTEENTH_NOTE
            # ...or otherwise is not the stop note
            elif row_note.note != XM_STOP_NOTE:
                # Trigger a new note
                midi_tracks[channel].append(
                    Message('note_on'
                            , channel=channel
                            , note=row_note.note + XM_TO_MIDI_PITCH
                            , time=TICKS_PER_SIXTEENTH_NOTE if not note_off_triggered else 0))

# Set first note in each track to start immediately
for track in midi_tracks:
    track[1].time = 0
midi_file.save('sample.mid')
