# Copyright 2021 The HuggingFace Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

import numpy as np
from huggingface_hub import AudioClassificationOutputElement

from mindnlp.transformers import MODEL_FOR_AUDIO_CLASSIFICATION_MAPPING
from mindnlp.transformers.pipelines import AudioClassificationPipeline, pipeline
from mindnlp.utils.testing_utils import (
    is_pipeline_test,
    nested_simplify,
    slow,
)

from .test_pipelines_common import ANY


@is_pipeline_test
class AudioClassificationPipelineTests(unittest.TestCase):
    model_mapping = MODEL_FOR_AUDIO_CLASSIFICATION_MAPPING

    def get_test_pipeline(
        self,
        model,
        tokenizer=None,
        image_processor=None,
        feature_extractor=None,
        processor=None,
        torch_dtype="float32",
    ):
        audio_classifier = AudioClassificationPipeline(
            model=model,
            tokenizer=tokenizer,
            feature_extractor=feature_extractor,
            image_processor=image_processor,
            processor=processor,
            torch_dtype=torch_dtype,
        )

        # test with a raw waveform
        audio = np.zeros((34000,))
        audio2 = np.zeros((14000,))
        return audio_classifier, [audio2, audio]

    def run_pipeline_test(self, audio_classifier, examples):
        audio2, audio = examples
        output = audio_classifier(audio)
        # by default a model is initialized with num_labels=2
        self.assertEqual(
            output,
            [
                {"score": ANY(float), "label": ANY(str)},
                {"score": ANY(float), "label": ANY(str)},
            ],
        )
        output = audio_classifier(audio, top_k=1)
        self.assertEqual(
            output,
            [
                {"score": ANY(float), "label": ANY(str)},
            ],
        )

        self.run_msaudio(audio_classifier)

    def run_msaudio(self, audio_classifier):
        import datasets

        # test with a local file
        dataset = datasets.load_dataset("hf-internal-testing/librispeech_asr_dummy", "clean", split="validation")
        audio = dataset[0]["audio"]["array"]
        output = audio_classifier(audio)
        self.assertEqual(
            output,
            [
                {"score": ANY(float), "label": ANY(str)},
                {"score": ANY(float), "label": ANY(str)},
            ],
        )

    def test_small_model_ms(self):
        model = "anton-l/wav2vec2-random-tiny-classifier"

        audio_classifier = pipeline("audio-classification", model=model)

        audio = np.ones((8000,))
        output = audio_classifier(audio, top_k=4)

        EXPECTED_OUTPUT = [
            {"score": 0.0842, "label": "no"},
            {"score": 0.0838, "label": "up"},
            {"score": 0.0837, "label": "go"},
            {"score": 0.0834, "label": "right"},
        ]
        EXPECTED_OUTPUT_PT_2 = [
            {"score": 0.0845, "label": "stop"},
            {"score": 0.0844, "label": "on"},
            {"score": 0.0841, "label": "right"},
            {"score": 0.0834, "label": "left"},
        ]
        self.assertIn(nested_simplify(output, decimals=4), [EXPECTED_OUTPUT, EXPECTED_OUTPUT_PT_2])

        audio_dict = {"array": np.ones((8000,)), "sampling_rate": audio_classifier.feature_extractor.sampling_rate}
        output = audio_classifier(audio_dict, top_k=4)
        self.assertIn(nested_simplify(output, decimals=4), [EXPECTED_OUTPUT, EXPECTED_OUTPUT_PT_2])

    @slow
    def test_large_model_ms(self):
        import datasets

        model = "superb/wav2vec2-base-superb-ks"

        audio_classifier = pipeline("audio-classification", model=model)
        dataset = datasets.load_dataset("anton-l/superb_dummy", "ks", split="test", trust_remote_code=True)

        audio = np.array(dataset[3]["speech"], dtype=np.float32)
        output = audio_classifier(audio, top_k=4)
        self.assertEqual(
            nested_simplify(output, decimals=3),
            [
                {"score": 0.981, "label": "go"},
                {"score": 0.007, "label": "up"},
                {"score": 0.006, "label": "_unknown_"},
                {"score": 0.001, "label": "down"},
            ],
        )