import torch
import torchaudio
from torchaudio.pipelines import MMS_FA as bundle


def test_forced_alignment(audio_filepath: str, expected_text: str):
    print(f"Loading audio from: {audio_filepath}")

    # 1. Load the Torchaudio MMS Forced Alignment bundle
    # This model is pre-trained on over 1,000 languages
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    model = bundle.get_model().to(device)
    tokenizer = bundle.get_tokenizer()
    aligner = bundle.get_aligner()

    # 2. Load the local audio file and resample it if necessary
    # The model expects a 16kHz sample rate
    waveform, sample_rate = torchaudio.load(audio_filepath)
    if sample_rate != bundle.sample_rate:
        waveform = torchaudio.functional.resample(waveform, sample_rate, bundle.sample_rate)

    # 3. Format the expected text
    # MMS_FA expects lowercase characters and we split the sentence into a list of words
    # e.g., ["the", "quick", "brown", "fox"]
    clean_text = expected_text.lower().replace(",", "").replace(".", "").replace("?", "")
    transcript_words = clean_text.split()

    print(f"Expected words: {transcript_words}")
    print("Running alignment... (this may take a few seconds on the first run as it downloads the model)")

    # 4. Generate the alignment
    with torch.inference_mode():
        # Get the acoustic features (emission) from the audio
        emission, _ = model(waveform.to(device))

        # Tokenize the words and run the aligner
        tokens = tokenizer(transcript_words)
        token_spans = aligner(emission[0], tokens)

    # 5. Calculate scores and map timestamps to the words
    results = []

    # Each word in the transcript gets a corresponding 'span' of audio frames
    for word, span in zip(transcript_words, token_spans):
        # Calculate the average confidence score for the word
        word_score = sum(s.score * len(s) for s in span) / sum(len(s) for s in span)

        # Convert frame indices to actual seconds based on the sample rate
        start_time = span[0].start / bundle.sample_rate
        end_time = span[-1].end / bundle.sample_rate

        results.append({
            "word": word,
            "start_time": round(start_time, 2),
            "end_time": round(end_time, 2),
            "score": round(float(word_score), 2)  # Closer to 1.0 is better
        })

    return results


if __name__ == "__main__":
    # --- CHANGE THESE TWO VARIABLES TO TEST ---
    SAMPLE_AUDIO_PATH = "audio_path/and he hides from the owl or vulture.wav"
    SAMPLE_EXPECTED_TEXT = "and he hides from the owl or vulture"
    # ------------------------------------------

    try:
        alignment_data = test_forced_alignment(SAMPLE_AUDIO_PATH, SAMPLE_EXPECTED_TEXT)

        print("\n--- ALIGNMENT RESULTS ---")
        for item in alignment_data:
            print(f"Word: {item['word']:<10} | "
                  f"Time: {item['start_time']:0.2f}s -> {item['end_time']:0.2f}s | "
                  f"Score: {item['score']}")

    except FileNotFoundError:
        print(f"\n❌ Error: Could not find the file '{SAMPLE_AUDIO_PATH}'.")
        print("Please place a valid .wav file in the same folder and update SAMPLE_AUDIO_PATH.")