<!-- image -->

This CVPR paper is the Open Access version, provided by the Computer Vision Foundation. Except for this watermark, it is identical to the accepted version; the final published version of the proceedings is available on IEEE Xplore.

## Ouroboros3D: Image-to-3D Generation via 3D-aware Recursive Diffusion

Hao Wen 1, 2 * Zehuan Huang 1,3 * Yaohui Wang 2 Xinyuan Chen 2 Lu Sheng 1† 1 School of Software, Beihang University 2 Shanghai AI Laboratory 3 VAST

Figure 1. Ouroboros3D generates multi-view consistent images and high-quality 3D models from single images using 3D-aware recursive diffusion, introducing a novel 3D-aware feedback mechanism that involves iterative cycles of multi-view denoising and reconstruction.

<!-- image -->

## Abstract

Existing image-to-3D creation methods typically split the task into two stages: multi-view image generation and 3D reconstruction, leading to two main limitations: (1) In multi-view generation stage, the multi-view generated images present a challenge to preserving 3D consistency; (2) In the 3D reconstruction stage, a domain gap exists between the real training data and the images generated during the inference process. To address these issues, we propose Ouroboros3D, an end-to-end trainable framework that integrates multi-view generation and 3D reconstruction into a recursive diffusion process through feedback mechanism. Our framework operates through iterative cycles where each cycle consists of a feedback denoising process and a reconstruction step. By incorporating a 3D-aware feedback mechanism, our multi-view generative model leverages the explicit 3D geometric information (e.g. texture, position) from the feedback of reconstruction results of the previous process as conditions, thus modeling consistency at the 3D geometric level. Furthermore, through joint training of both the multi-view generative and reconstruction models, we alleviate reconstruction stage domain gap and enable mutual enhancement within the recursive process. Experimental results demonstrate that Ouroboros3D outperforms methods that treat these stages separately and those that combine them only during inference, achieving superior multi-view consistency and producing 3D models with higher geometric realism. Please see the project page at https://costwen.github.io/Ouroboros3D/

* Equal contribution

† Corresponding author

Figure 2. Concept comparison between Ouroboros3D and previous two-stage methods. Instead of separating multi-view diffusion model and reconstruction model, our framework involves joint training and inference of these two models, which are established into a recursive diffusion process.

<!-- image -->

## 1. Introduction

Creating 3D content from a single image have achieved rapid progress in recent years with the adoption of large-scale 3D datasets [6, 7, 54] and generative models [12, 44, 45]. A body of research [20, 23, 28-30, 42, 47, 49] has focused on multi-view generation, fine-tuning pretrained image or video diffusion models on 3D datasets to enable consistent multiview synthesis. These methods demonstrate generalizability and produce promising results. Another group of works [15, 46, 53, 56, 58] propose generalizable reconstruction models, to generate 3D representation from one or few views in a feed-forward process, leading to efficient image-to-3D creation.

Since single-view reconstruction models [15] trained on 3D datasets [6, 60] lack generalizability and often produce blurring at unseen viewpoints, several works [24, 46, 53, 56] combine multi-view diffusion models and feed-forward reconstruction models, so as to extend the reconstruction stage to sparse-view input, boosting the reconstruction quality. As shown in Fig. 2, these methods split 3D generation into two stages: multi-view synthesis and 3D reconstruction. By combining generalizable multi-view diffusion models and robust sparse-view reconstruction models, such pipelines achieve high-quality image to 3D generation. However, combining the two independently designed models introduces a significant limitation to the reconstruction model. Data bias manifests primarily in two aspects: (1) In multi-view generation stage, multi-view diffusion model is optimized at the image level, not in 3D space, complicating the assurance of geometric consistency. (2) In 3D reconstruction stage, reconstruction model is trained primarily on synthetic data with limited real data, suffering from domain gap when processing generated multi-view images.

Recent works have explored several mechanisms to enhance multi-view consistency. Carve3D [55] employs a RL-based fine-tuning algorithm [2], applying a multi-view consistency metric to enhance the multi-view image gen- eration. However, the challenge of data limitation has not been well-addressed, leading to poor reconstruction quality. On the other hand, IM-3D [32] and VideoMV [65] aggregate the rendered views of the reconstructed 3D model into multi-view synthesis during inference by adopting resampling strategy in the denoising loop. However, on the overall image-to-3D pipeline, it (a) lacks joint training and (b) inability to use space information hinder its capacity to fully leverage 3D-aware knowledge and unify the two stages. Moreover, these methods fail to address the domain gap between generated multi-view images and training data in 3D reconstruction stage, and the use of biased information from few-shot reconstructed 3D models can result in multi-view outputs misaligned with the input image (see Fig. 5).

In this paper, we introduce Ouroboros3D, a novel imageto-3D framework that seamlessly integrates multi-view generation with 3D reconstruction within a recursive diffusion process, as depicted in Fig. 3. To facilitate the modeling of multi-view consistency, we propose a 3D-aware feedback mechanism, where our multi-view diffusion model utilizes 3D-aware maps rendered by the reconstruction module from the previous timestep as additional conditions during the denoising phase. Leveraging 3D-aware feedback from reconstructed representations, our model produces images with enhanced geometric consistency. To address the domain gap between the reconstruction stage training data and generated multi-view data, we involve joint training of the multi-view diffusion model and reconstruction model. During training, the reconstruction model utilizes images restored by the diffusion process rather than original images. Joint training two module not only reduces the domain gap in the reconstruction stage, increasing the diversity of the reconstruction, but also enhances the capability of diffusion model to generate images better suited for few-shot reconstruction (consider reconstruction model as a criterion to supervise multi-view diffusion model), making the two stages mutually beneficial in the multi-step iterative diffusion process. The 3D-aware recursived diffusion, with the integration of the two stages, facilitates adaptive refinement of outputs through mutual feedback, enhancing inference stability and reducing data bias.

Experimental results on the GSO dataset [9] show that our framework outperforms separation of these stages and existing methods [65] that combine the stages at the inference phase.

Our key contributions are as follows:

- We introduce a image-to-3D creation framework Ouroboros3D, which integrates multi-view generation and 3D reconstruction into a recursive diffusion process. The framework is highly extensible and can accommodate various multi-view generation networks and reconstruction networks.
- Ouroboros3D employs 3D-aware feedback mechanism, using rendered maps to guide the multi-view generation, ensuring better geometric consistency and robustness.
- We conducte extensive experiments to demonstrate that Ouroboros3D significantly reduces reconstruction inference domain gap and outperforms both the method that separates the two stages and the method that combines them only at inference time.

## 2. Related Work

Image/Video Diffusion for Multi-view Generation Diffusion models [3, 4, 8, 13, 14, 16, 17, 31, 36, 39-41, 43, 52] have demonstrated their powerful generative capabilities in image and video generation fields. Current research [19, 20, 23, 28-30, 42, 47, 49, 61, 63] fine-tunes pretrained image/video diffusion models on 3D datasets like Objaverse [6] and MVImageNet [60]. Zero123 [28] introduces relative view condition to image diffusion models, enabling novel view synthesis from a single image and preserving generalizability. Based on it, methods like SyncDreamer [29], ConsistNet [59] and EpiDiff [20] design attention modules to generate consistent multi-view images. These methods fine-tuned from image diffusion models produce generally promising results. By considering multi-view images as consecutive frames of a video (e.g., orbiting camera views), it naturally leads to the idea of applying video generation models to 3D generation [49]. However, since the diffusion model is not explicitly modeled in 3D space, the generated multi-view images often struggle to achieve consistent and robust details.

Image to 3D Reconstruction Recently, the task of reconstructing 3D objects has evolved from traditional multi-view reconstruction methods [1, 22, 33, 35] to feed-forward reconstruction models [15, 18, 21, 46, 53, 56, 58, 64]. Ultilizing one or few shot as input, these highly generalizable reconstruction models synthesize 3D representation, enabling the rapid generation of 3D objects. LRM [15] proposes a transformer-based model to effectively map image tokens to

Figure 3. Overview of 3D-aware recursive diffusion. During multi-view denoising, the diffusion model uses 3D-aware maps rendered by the reconstruction module at the previous step as conditions.

<!-- image -->

3D triplanes. Instant3D [24] further extends LRM to sparseview input, significantly boosting the reconstruction quality. LGM [46] and GRM [58] replace the triplane representation with 3D Gaussians [22] to enjoy its superior rendering efficiency. CRM [53] and InstantMesh [56] optimize on the mesh representation for high-quality geometry and texture modeling. These reconstrucion models built upon convolutional network architecture or transformer backbone, have led to efficient image-to-3D creation.

Pipelines of 3D Generation Early works propose to distill knowledge of image prior to create 3D models via Score Distillation Sampling (SDS) [11, 26, 37], limited by the low speed of per-scene optimization. DMV3D [57] employs a 3D reconstruction model as the 2D multi-view denoiser in a multiview diffusion framework, to achieve generic end-toend 3D generation. However, it fails to utilize the advanced features of pre-existing image or video diffusion models, and training from scratch on 3D data limits its generalization. Several works [20, 29, 30, 32] fine-tune image diffusion models to generate multi-view images, which are then utilized for 3D shape and appearance recovery with traditional reconstruction methods [22, 51]. More recently, several works [24, 46, 53, 56, 65] involve both multi-view diffusion models and feed-forward reconstruction models in the generation process. Such pipelines attempt to combine the processes into a cohesive two-stage approach, thus achieving highly generalizable and high-quality single-image to 3D generation. The multi-view diffusion model, lacking explicit 3D modeling, struggles to ensure strong consistency, resulting in data deviations between the testing and training phases. In contrast, we propose a unified pipeline that integrates these stages through a self-conditioning mechanism during training, enhanced by 3D-aware feedback to achieve high consistency.

## 3. Method

Given a single image, Ouroboros3D aims to generate multiview-consistent images with a reconstructed 3D Gaussion model. To reduce the domain gap and improve robustness of the generation, our framework integrates multiview synthesis and 3D reconstruction in a recursive diffusion process. As illustrated in Fig. 4, the proposed framework involves a video diffusion model (SVD [3]) as multi-view generator (refer to Sec. 3.1) and a feed-forward reconstruction model to recover a 3D Gaussian Splatting (refer to Sec. 3.2. Moreover, we introduce a self-conditioning mechanism, feeding the 3D-aware information obtained from the reconstruction module back to the multi-view generation process (refer to Sec. 3.3). The 3D-aware recursive diffusion strategy iteratively refines the multi-view images and the 3d model, enhancing the final production.

## 3.1. Video Diffusion Model as Multiview Generator

Recent video diffusion models [4, 10, 49] have demonstrated a remarkable capability to generate 3D-aware videos. We employs the well-known Stable Video Diffusion (SVD) Model as our multi-view generator, which generates videos from an image input. In our framework, we set the number of the generated frames f to 8.

We enhance the video diffusion model with camera control c to generate images from different viewpoints. Traditional methods encode camera positions at the frame level, which results in all pixels within one view sharing the same positional encoding [27, 49]. Building on the innovations of previous work [20, 63], we integrate the camera condition c into the denoising network by parameterizing the rays r = ( o, o × d ) . Specifically, we use two-layered MLP to inject Plücker ray embeddings for each latent pixel, enabling precise positional encoding at the pixel level. This approach allows for more detailed and accurate 3D rendering, as pixelspecific embedding enhances the model's ability to handle complex variations in depth and perspective across the video frames.

Our multi-view diffusion model differs from existing twostage methods in that it does not independently complete all denoising steps. Instead, within the denoising sampling loop, we obtain the predicted ˜ x f 0 at each timestep, where f indicates the frame number, which is then utilized for subsequent 3D reconstruction. The rendered maps are employed as conditions to guide the next denoising step. At each sampling step,we reparameterize the output from the denoising network F θ to transform it into ˜ x f 0 . we apply the following formula to process the noising images c in ( σ ) x f and the associated noise level c noise ( σ ) :

<!-- formula-not-decoded -->

where σ indicates the standard deviation of the noise, c skip is a parameter that controls how much of the original x f 0 is retained. This operation adjusts the output of F θ to ˜ x f 0 , which will be decoded into images and passed to the subsequent 3D reconstruction module.

## 3.2. Feed-Forward Reconstruction Model

In the Ouroboros3D framework, the feed-forward reconstruction model is designed to recover 3D models from pregenerated multi-view images, which can be images decoded from straightly predicted ˜ x f 0 , or completely denoised images. We utilize Large Multi-View Gaussian Model (LGM) [46] G as our reconstruction module due to its real-time rendering capabilities that benefit from 3D representation of Gaussian Splatting.

We pass four specific views from the reparameterized output ˜ x f 0 to the Large Gaussian Model (LGM) for 3D Gaussian Splatting reconstruction. To enhance the performance of LGM, particularly its sensitivity to different noise levels c noise ( σ ) and image details, we introduce a zero-initialized time embedding layer within the original U-Net structure of the LGM. During training, we use 8 multi-view images encircling the object and 4 random views to supervise the model.

The loss function employed for the fine-tuning of the LGM is articulated as follows:

<!-- formula-not-decoded -->

where I represents the set of supervised multiview images, C is the corresponding camera parameters.

Additionally, to maintain the model's reconstruction capability for normal images, we also input the model without adding noise and calculate the corresponding loss. In this case, we set c noise ( σ ) to 0.

## 3.3. 3D-Aware Feedback Mechanism

We use a 3D-aware feedback mechanism, as shown in Fig. 4, involving rendered color images and geometric maps in a denoising loop to enhance multiview consistency and facilitate cyclic adaptation. Unlike integrating multi-view generation and 3D reconstruction at the inference stage using re-sampling strategy [32, 65], we jointly train these two modules to support more informative feedback.

In practice, we obtain color images and canonical coordinates maps (CCM) [25] from the reconstructed 3D model, and utilize them as condition to guide the next denoising step of multi-view generation. We choose CCM over depth or normal maps because CCMs capture global vertex coordinates normalized across the entire 3D model, unlike depth maps that normalize relative to the self-view. This operation enables the rendered maps to be characterized as cross-view alignment, providing the strong guidance of more explicit cross-view geometry relationship.

Figure 4. Overview of Ouroboros3D. We adopt a video diffusion model as the multi-view generator by incorporating the input image and relative camera poses. In the denoising sampling loop, we decode the predicted ˜ x f 0 to noise-corrupted images, which are then used to recover 3D representation by a feed-forward reconstruction model. Then the rendered color images and coordinates maps are encoded and fed into the next denoising step. At inference, the 3D-aware denoising sampling strategy iteratively refines the images by incorporating feedback from the reconstructed 3D into the denoising loop, enhancing multi-view consistency and image quality.

<!-- image -->

To encode color images and coordinates maps into the denoising network of multi-view generation module, we design two simple and lightweight encoders for color images and coordinates maps using a series of convolutional neural networks, like T2I-Adapter [34]. The encoders are composed of four feature extraction blocks and three downsample blocks to change the feature resolution, so that the dimension of the encoded features is the same as the intermediate feature in the encoder of U-Net denoiser. The extracted features from the two conditional modalities are then added to the U-Net encoder at each scale.

We then introduce the proposed 3D-aware selfconditioning [5] strategy for both training and inference. The original multi-view denoising network F θ ( x ; σ ) is augmented with 3D-aware feedback, formulated as F θ ( x ; σ, G (˜ x 0 )) , where G (˜ x 0 ) is the rendered maps of the reconstruction module.

Training Strategy The training of the 3D-aware multiview generation network involves a probabilistic selfconditioning mechanism. During each training iteration, the network uses the rendered results from a feed-forward model as self-conditioning input with a probability of 0.5. This approach ensures balanced learning and prevents the model from over-relying on the 3D information. We use the reconstruction module to lift multi-view information into explicit 3D representation, and render it to geometrically aligned RGB and CCM views, which subsequently guide the multi-view generation.The detail of training algorithm can be seen in supplementary material.

Inference Strategy In inference stage, the initial condition G (˜ x 0 ) is set to zero. At each subsequent timestep, this 3D condition is updated based on the previous reconstruction result, then as a self feedback mechanism to guidance next denoising process. This iterative updating process refines the 3D representation, enhancing the consistency of multi-view images and improving the quality of the reconstructed 3D models. The detail of inference algorithm can be seen in supplementary material.

## 4. Experiments

## 4.1. Implementation Details

Datasets We use a filtered subset of the Objaverse [6] dataset to train our model. Following LGM [46], we implemented a rigorous filtering process to remove bad models with bad captions or missing texture. It leads to a final set of around 80K 3D objects. We render 2 16-frame RGBA orbits at 512 × 512 . For each orbit, the cameras are positioned at a randomly sampled elevation between [-5, 30] degrees. During training, we subsample any 8-frame orbit by picking any frame in one orbit as the first frame (the conditioning image), and then choose every 2nd frame after that.

We evaluate the synthesized multi-view images and reconstructed 3D Gaussian Splatting (3DGS) on the unseen GSO [9] dataset. We filter 100 objects to reduce redundancy and maintain diversity then render ground truth orbit videos and pick the first frame as the conditioning image.

Figure 5. Qualitative comparisons of generated multi-view images. Our method achieves better consistency and quality.

<!-- image -->

Figure 6. Qualitative comparisons for image-to-3D generation.

<!-- image -->

Table 1. Quantitative comparison on the quality of generated multiview (MV.) images and 3D representation for image-to-multiview and image-to-3D tasks.

|     | Method           |   Res |   PSNR ↑ |   SSIM ↑ |   LPIPS ↓ |
|-----|------------------|-------|----------|----------|-----------|
| MV. | VideoMV [65]     |   256 |   18.605 |   0.8410 |    0.1548 |
| MV. | SyncDreamer [29] |   256 |   20.056 |   0.8163 |    0.1596 |
| MV. | SV3D [49]        |   576 |   21.042 |   0.8497 |    0.1296 |
| MV. | Ouroboros3D      |   512 |   21.770 |   0.8866 |    0.1093 |
|     | LGM [46]         |   512 |   17.716 |   0.8319 |    0.1894 |
|     | TripoSR [48]     |   256 |   18.481 |   0.8506 |    0.1357 |
| 3D  | VideoMV(GS) [65] |   256 |   18.764 |   0.8449 |    0.1569 |
| 3D  | InstantMesh [56] |   512 |   19.948 |   0.8727 |    0.1205 |
| 3D  | Ouroboros3D      |   512 |   21.761 |   0.8894 |    0.1091 |

Experimental Settings Our Ouroboros3D is trained for 30,000 iterations using 8 A100 GPUs with a total batch size of 32. We clip the gradient with a maximum norm of 1.0. We use the AdamW optimizer with a learning rate of 1 × 10 -5 and employ FP16 mixed precision with DeepSeed[38] with Zero-2 for efficient training. At the inference stage, we set the number of sampling steps as 25, which takes about 20 seconds to generate a 3d model.

Metrics We compare generated multi-view images and rendered views from reconstructed 3DGS with the ground truth frames, in terms of Learned Perceptual Similarity (LPIPS [62]), Peak Signal-to-Noise Ratio (PSNR), and Structural SIMilarity (SSIM).

Baselines In terms of multi-view generation, we compare Ouroboros3D with SyncDreamer [29], SV3D [49], VideoMV [65]. For image-to-3D creation, we adopt feed-forward reconstruction models or pipelines as baseline methods, including TripoSR [48], LGM [46] and InstantMesh(Nerf) [56], where LGM and InstantMesh adopt two-stage methods to achieve image-to-3D creation.

## 4.2. Comparison with Existing Alternatives

Image-to-Multiview generation Wecompare our method with SyncDreamer [29], SV3D [49] and VideoMV [65], as shown in Fig. 5. SyncDreamer and SV3D fine-tune image or video diffusion models on 3D datasets but lack explicit 3D information, often resulting in blurry textures or inconsistent details. VideoMV aggregates rendered views from reconstructed 3D models at the inference stage but fails to take into account the domain gap between two stages. Although VideoMV improves the multi-view consistency, it introduces biased information from the reconstruction stage, leading to results that are unaligned with the input image. Our Ouroboros3D uses joint training of the two stages and uses geometry and appearance feedback for multi-view generation, generating consistent and high-quality multi-view images.

Table 2. Ablation study of different feedback mechanisms. Results show that our 3D-aware feedback mechanism lead to superior generalization performance. For implementations involving feedback, we employ the joint training strategy for model optimization.

| Joint Training   | CCM Feedback   | RGB Feedback   |   PSNR ↑ |   SSIM ↑ |   LPIPS ↓ |   ∆ PSNR ↓ |   ∆ SSIM ↓ |   ∆ LPIPS ↓ |
|------------------|----------------|----------------|----------|----------|-----------|------------|------------|-------------|
| ✗                | ✗              | ✗              |   20.012 |   0.8465 |    0.1287 |      1.067 |     0.0125 |      0.0189 |
| ✓                | ✗              | ✗              |   20.549 |   0.8651 |    0.1183 |      0.511 |     0.0094 |      0.0070 |
| ✓                | ✓              | ✗              |   21.325 |   0.8937 |    0.1092 |      0.304 |     0.0036 |      0.0018 |
| ✓                | ✗              | ✓              |   21.542 |   0.8871 |    0.1103 |      0.100 |     0.0101 |      0.0036 |
| ✓                | ✓              | ✓              |   21.761 |   0.9094 |    0.0991 |      0.009 |     0.0028 |      0.0002 |

Figure 7. Qualitative ablation study on the reconstruction results with two types of feedback.

<!-- image -->

Image-to-3D generation We compare our method with TripoSR [48], VideoMV [65], LGM [46] and InstantMesh [56], as visualized in Fig. 6. TripoSR struggles with high-quality geometry and appearance due to lacking large pre-trained generative models. VideoMV reconstructs 3DGS from its generated multi-view images, but its inherent biases in multiview generation can lead to misaligned textures and distorted geometries. Two-stage methods such as LGM and InstantMesh, which comprise an off-the-shelf image-to-multiview generation method followed by reconstruction models for the image-to-3D generation process, often yield incomplete geometry due to the disparity between multiview generation and 3D reconstruction. In contrast, our framework integrates multiview generation and 3D reconstruction, enhancing each module's strengths to produce high-quality 3D assets.

Generalizability Ouroboros3D exhibits remarkable generalizability, adept at producing high-quality 3D models from images that fall outside its training distribution, including real-world images. This capability is demonstrated in the results shown in Fig. 8 and supplementary materials.

## 4.3. Ablation Study

To assess the effectiveness of our 3D-aware feedback mechanism, we conducted ablation experiments on the generated 3DGS for different configurations (Fig. 7 and Tab. 2). We start with a base framework that does not jointly trains the multi-view generation module and the reconstruction module, or use feedback mechanism. We then incrementally add components of our proposed approach.

Table 3. Ablation on feedback steps

| Feedback Steps   |   PSNR ↑ |   SSIM ↑ |   LPIPS ↓ |
|------------------|----------|----------|-----------|
| 0 ∼ 25           |   21.761 |   0.9094 |    0.0991 |
| 10 ∼ 25          |   21.633 |   0.9099 |    0.1021 |
| 20 ∼ 25          |   20.805 |   0.8957 |    0.1101 |

The reconstructed results shown in Fig. 7 demonstrate that, only the coordinates map feedback produces blurry textures, and only the color map has poor geometric quality in fine details. Our full setting leads to superior performance in both geometry and texture. Tab. 2 reports the quantitative results, which demonstrate significant improvements by enhancing both geometric consistency and texture details. We also report the absolute distances of performance metrics between the generated multiviews and 3DGS. It can be observed that our framework reduces the performance difference between the generated multi-view images and 3D representation, and improves the combined performance.

Figure 8. Ouroboros3D can generate high-quality 3D models given image inputs outside the distribution, including real world images.

<!-- image -->

Table 4. Comparison of training and inference speed. Left: training time for 1,000 steps; Right: inference time per sample.

| Setting     | Training Time   | Setting     | Inference Time   |
|-------------|-----------------|-------------|------------------|
| SVD         | 15 min          | LGM         | 1.225s           |
| LGM         | 10 min          | SV3D + LGM  | 24.18s           |
| Ouroboros3D | 36 min          | Ouroboros3D | 25.19s           |

We conduct the experiments on the feedback steps. As shown in Tab. 3, excluding feedback for the first 10 steps yields comparable results to the full setting, whereas excluding it for 20 steps reduces performance.

## 4.4. Discussion

Recursive Generation Process We visualize the reconstruction process at different denoising steps in the supplementary materials. Early stages show floating artifacts and distorted geometries due to multi-view inconsistency. As denoising progresses, our recursive diffusion method gradually refines both the geometric accuracy and material properties of the reconstruction. Compare to no feedback results, the model achieves better shape and texture refinement during early stages with the feedback mechanism.

Alternative 3D Representations Our model currently utilize 3D Gaussian splatting as the generated 3D representation, which is not as widely used as meshes. Replacing the reconstruction module with CRM [53] or InstantMesh [56] can enable our framework to generate meshes from a single image. In addition, experiments on 3D scene dataset will also be an extension of our framework.

## 4.5. Limitation

Training and Inference Efficiency While our joint training method enhances model performance, it increases re- quires additional time and more GPU memory . We measure the time required for 1,000 training steps on an A100 GPU. As shown in Tab. 4, Ouroboros3D takes longer to train than the individual components when trained separately, primarily due to the extra computations and the need for 3d feedback.

We also evaluate the inference speed of baseline methods under identical settings to ensure fairness. Despite the higher training cost, the results showed that the inference efficiency of our method is comparable to that of the baselines. The LGM baseline employs ImageDream [50] to generate 4 views at 256 × 256 resolution, which are then reconstructed into a 3D Gaussian Splatting (3DGS) representation. In contrast, our Ouroboros3D approach utilizes SVD to generate 8 views at 512 × 512 resolution. For a fair comparison, we report the inference time of "SV3D + LGM", where SV3D [49] is a multi-view generator finetuned from SVD. Compared to it, the additional overhead in our method mainly stems from the feedback mechanism at each step, involving VAE decoding, 3D reconstruction and conditioning injection. However, the impact on inference speed is minimal, rendering Ouroboros3D efficient for practical applications once training is complete.

## 5. Conclusion

In this paper, we introduce Ouroboros3D, a unified framework for single image-to-3D creation that integrates multiview image generation and 3D reconstruction in a recursive diffusion process. In our framework, these two modules are jointly trained through a self-conditioning mechanism, which allows them to adapt to the inherent characteristic of each stage. By establishing a recursive relationship between these two stages through a 3d aware feedback mechanism, our approach effectively mitigates the data bias encountered in existing two-stage methods.

## Acknowledgment

This work was supported by National Natural Science Foundation of China (62132001), and the Fundamental Research Funds for the Central Universities.

## References

- [1] Jonathan T Barron, Ben Mildenhall, Matthew Tancik, Peter Hedman, Ricardo Martin-Brualla, and Pratul P Srinivasan. Mip-nerf: A multiscale representation for anti-aliasing neural radiance fields. In Proceedings of the IEEE/CVF International Conference on Computer Vision , pages 5855-5864, 2021. 3
- [2] Kevin Black, Michael Janner, Yilun Du, Ilya Kostrikov, and Sergey Levine. Training diffusion models with reinforcement learning. arXiv preprint arXiv:2305.13301 , 2023. 2
- [3] Andreas Blattmann, Tim Dockhorn, Sumith Kulal, Daniel Mendelevitch, Maciej Kilian, Dominik Lorenz, Yam Levi, Zion English, Vikram Voleti, Adam Letts, et al. Stable video diffusion: Scaling latent video diffusion models to large datasets. arXiv preprint arXiv:2311.15127 , 2023. 3, 4
- [4] Tim Brooks, Bill Peebles, Connor Holmes, Will DePue, Yufei Guo, Li Jing, David Schnurr, Joe Taylor, Troy Luhman, Eric Luhman, Clarence Ng, Ricky Wang, and Aditya Ramesh. Video generation models as world simulators, 2024. 3, 4
- [5] Ting Chen, Ruixiang Zhang, and Geoffrey Hinton. Analog bits: Generating discrete data using diffusion models with self-conditioning. arXiv preprint arXiv:2208.04202 , 2022. 5
- [6] Matt Deitke, Dustin Schwenk, Jordi Salvador, Luca Weihs, Oscar Michel, Eli VanderBilt, Ludwig Schmidt, Kiana Ehsani, Aniruddha Kembhavi, and Ali Farhadi. Objaverse: A universe of annotated 3d objects. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition , pages 13142-13153, 2023. 2, 3, 5
- [7] Matt Deitke, Ruoshi Liu, Matthew Wallingford, Huong Ngo, Oscar Michel, Aditya Kusupati, Alan Fan, Christian Laforte, Vikram Voleti, Samir Yitzhak Gadre, et al. Objaverse-xl: A universe of 10m+ 3d objects. Advances in Neural Information Processing Systems , 36, 2024. 2
- [8] Junting Dong, Qi Fang, Zehuan Huang, Xudong Xu, Jingbo Wang, Sida Peng, and Bo Dai. Tela: Text to layer-wise 3d clothed human generation. In European Conference on Computer Vision , pages 19-36. Springer, 2024. 3
- [9] Laura Downs, Anthony Francis, Nate Koenig, Brandon Kinman, Ryan Hickman, Krista Reymann, Thomas B McHugh, and Vincent Vanhoucke. Google scanned objects: A highquality dataset of 3d scanned household items. In 2022 International Conference on Robotics and Automation (ICRA) , pages 2553-2560. IEEE, 2022. 3, 6
- [10] Ruiqi Gao, Aleksander Holynski, Philipp Henzler, Arthur Brussee, Ricardo Martin-Brualla, Pratul Srinivasan, Jonathan T Barron, and Ben Poole. Cat3d: Create anything in 3d with multi-view diffusion models. arXiv preprint arXiv:2405.10314 , 2024. 4
- [11] Yuan-Chen Guo, Ying-Tian Liu, Ruizhi Shao, Christian Laforte, Vikram Voleti, Guan Luo, Chia-Hao Chen, ZiXin Zou, Chen Wang, Yan-Pei Cao, and Song-Hai Zhang. threestudio: A unified framework for 3d content generation.
12. https://github.com/threestudio-project/ threestudio , 2023. 3
- [12] Jonathan Ho, Ajay Jain, and Pieter Abbeel. Denoising diffusion probabilistic models. Advances in neural information processing systems , 33:6840-6851, 2020. 2
- [13] Jonathan Ho, William Chan, Chitwan Saharia, Jay Whang, Ruiqi Gao, Alexey Gritsenko, Diederik P Kingma, Ben Poole, Mohammad Norouzi, David J Fleet, et al. Imagen video: High definition video generation with diffusion models. arXiv preprint arXiv:2210.02303 , 2022. 3
- [14] Jonathan Ho, Tim Salimans, Alexey Gritsenko, William Chan, Mohammad Norouzi, and David J Fleet. Video diffusion models. Advances in Neural Information Processing Systems , 35:8633-8646, 2022. 3
- [15] Yicong Hong, Kai Zhang, Jiuxiang Gu, Sai Bi, Yang Zhou, Difan Liu, Feng Liu, Kalyan Sunkavalli, Trung Bui, and Hao Tan. Lrm: Large reconstruction model for single image to 3d. arXiv preprint arXiv:2311.04400 , 2023. 2, 3
- [16] Li Hu. Animate anyone: Consistent and controllable imageto-video synthesis for character animation. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition , pages 8153-8163, 2024. 3
- [17] Zehuan Huang, Hongxing Fan, Lipeng Wang, and Lu Sheng. From parts to whole: A unified reference framework for controllable human image generation. arXiv preprint arXiv:2404.15267 , 2024. 3
- [18] Zehuan Huang, Yuan-Chen Guo, Xingqiao An, Yunhan Yang, Yangguang Li, Zi-Xin Zou, Ding Liang, Xihui Liu, YanPei Cao, and Lu Sheng. Midi: Multi-instance diffusion for single image to 3d scene generation. arXiv preprint arXiv:2412.03558 , 2024. 3
- [19] Zehuan Huang, Yuan-Chen Guo, Haoran Wang, Ran Yi, Lizhuang Ma, Yan-Pei Cao, and Lu Sheng. Mv-adapter: Multi-view consistent image generation made easy. arXiv preprint arXiv:2412.03632 , 2024. 3
- [20] Zehuan Huang, Hao Wen, Junting Dong, Yaohui Wang, Yangguang Li, Xinyuan Chen, Yan-Pei Cao, Ding Liang, Yu Qiao, Bo Dai, et al. Epidiff: Enhancing multi-view synthesis via localized epipolar-constrained diffusion. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition , pages 9784-9794, 2024. 2, 3, 4
- [21] Hanwen Jiang, Zhenyu Jiang, Yue Zhao, and Qixing Huang. Leap: Liberate sparse-view 3d modeling from camera poses. arXiv preprint arXiv:2310.01410 , 2023. 3
- [22] Bernhard Kerbl, Georgios Kopanas, Thomas Leimkuehler, and George Drettakis. 3d gaussian splatting for real-time radiance field rendering. ACM Transactions on Graphics (TOG) , 42(4):1-14, 2023. 3
- [23] Jeong-gi Kwak, Erqun Dong, Yuhe Jin, Hanseok Ko, Shweta Mahajan, and Kwang Moo Yi. Vivid-1-to-3: Novel view synthesis with video diffusion models. arXiv preprint arXiv:2312.01305 , 2023. 2, 3
- [24] Jiahao Li, Hao Tan, Kai Zhang, Zexiang Xu, Fujun Luan, Yinghao Xu, Yicong Hong, Kalyan Sunkavalli, Greg Shakhnarovich, and Sai Bi. Instant3d: Fast text-to-3d with sparse-view generation and large reconstruction model. arXiv preprint arXiv:2311.06214 , 2023. 2, 3

- [25] Weiyu Li, Rui Chen, Xuelin Chen, and Ping Tan. Sweetdreamer: Aligning geometric priors in 2d diffusion for consistent text-to-3d. arXiv preprint arXiv:2310.02596 , 2023. 4
- [26] Chen-Hsuan Lin, Jun Gao, Luming Tang, Towaki Takikawa, Xiaohui Zeng, Xun Huang, Karsten Kreis, Sanja Fidler, MingYu Liu, and Tsung-Yi Lin. Magic3d: High-resolution textto-3d content creation. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition , pages 300-309, 2023. 3
- [27] Ruoshi Liu, Rundi Wu, Basile Van Hoorick, Pavel Tokmakov, Sergey Zakharov, and Carl Vondrick. Zero-1-to-3: Zero-shot one image to 3d object. In Proceedings of the IEEE/CVF International Conference on Computer Vision , pages 92989309, 2023. 4
- [28] Ruoshi Liu, Rundi Wu, Basile Van Hoorick, Pavel Tokmakov, Sergey Zakharov, and Carl Vondrick. Zero-1-to-3: Zero-shot one image to 3d object. In Proceedings of the IEEE/CVF International Conference on Computer Vision , pages 92989309, 2023. 2, 3
- [29] Yuan Liu, Cheng Lin, Zijiao Zeng, Xiaoxiao Long, Lingjie Liu, Taku Komura, and Wenping Wang. Syncdreamer: Generating multiview-consistent images from a single-view image. arXiv preprint arXiv:2309.03453 , 2023. 3, 6, 7
- [30] Xiaoxiao Long, Yuan-Chen Guo, Cheng Lin, Yuan Liu, Zhiyang Dou, Lingjie Liu, Yuexin Ma, Song-Hai Zhang, Marc Habermann, Christian Theobalt, et al. Wonder3d: Single image to 3d using cross-domain diffusion. arXiv preprint arXiv:2310.15008 , 2023. 2, 3
- [31] Xin Ma, Yaohui Wang, Gengyun Jia, Xinyuan Chen, Ziwei Liu, Yuan-Fang Li, Cunjian Chen, and Yu Qiao. Latte: Latent diffusion transformer for video generation. arXiv preprint arXiv:2401.03048 , 2024. 3
- [32] Luke Melas-Kyriazi, Iro Laina, Christian Rupprecht, Natalia Neverova, Andrea Vedaldi, Oran Gafni, and Filippos Kokkinos. Im-3d: Iterative multiview diffusion and reconstruction for high-quality 3d generation. arXiv preprint arXiv:2402.08682 , 2024. 2, 3, 4
- [33] Ben Mildenhall, Pratul P Srinivasan, Matthew Tancik, Jonathan T Barron, Ravi Ramamoorthi, and Ren Ng. Nerf: Representing scenes as neural radiance fields for view synthesis. Communications of the ACM , 65(1):99-106, 2021. 3
- [34] Chong Mou, Xintao Wang, Liangbin Xie, Yanze Wu, Jian Zhang, Zhongang Qi, and Ying Shan. T2i-adapter: Learning adapters to dig out more controllable ability for text-to-image diffusion models. In Proceedings of the AAAI Conference on Artificial Intelligence , pages 4296-4304, 2024. 5
- [35] Thomas Müller, Alex Evans, Christoph Schied, and Alexander Keller. Instant neural graphics primitives with a multiresolution hash encoding. ACM transactions on graphics (TOG) , 41(4):1-15, 2022. 3
- [36] Dustin Podell, Zion English, Kyle Lacey, Andreas Blattmann, Tim Dockhorn, Jonas Müller, Joe Penna, and Robin Rombach. Sdxl: Improving latent diffusion models for high-resolution image synthesis. arXiv preprint arXiv:2307.01952 , 2023. 3
- [37] Ben Poole, Ajay Jain, Jonathan T Barron, and Ben Mildenhall.
14. Dreamfusion: Text-to-3d using 2d diffusion. arXiv preprint arXiv:2209.14988 , 2022. 3
- [38] Jeff Rasley, Samyam Rajbhandari, Olatunji Ruwase, and Yuxiong He. Deepspeed: System optimizations enable training deep learning models with over 100 billion parameters. In Proceedings of the 26th ACM SIGKDD International Conference on Knowledge Discovery &amp; Data Mining , pages 3505-3506, 2020. 6
- [39] Robin Rombach, Andreas Blattmann, Dominik Lorenz, Patrick Esser, and Björn Ommer. High-resolution image synthesis with latent diffusion models. In Proceedings of the IEEE/CVF conference on computer vision and pattern recognition , pages 10684-10695, 2022. 3
- [40] Chitwan Saharia, William Chan, Saurabh Saxena, Lala Li, Jay Whang, Emily L Denton, Kamyar Ghasemipour, Raphael Gontijo Lopes, Burcu Karagol Ayan, Tim Salimans, et al. Photorealistic text-to-image diffusion models with deep language understanding. Advances in neural information processing systems , 35:36479-36494, 2022.
- [41] Axel Sauer, Frederic Boesel, Tim Dockhorn, Andreas Blattmann, Patrick Esser, and Robin Rombach. Fast highresolution image synthesis with latent adversarial diffusion distillation. arXiv preprint arXiv:2403.12015 , 2024. 3
- [42] Yichun Shi, Peng Wang, Jianglong Ye, Mai Long, Kejie Li, and Xiao Yang. Mvdream: Multi-view diffusion for 3d generation. arXiv preprint arXiv:2308.16512 , 2023. 2, 3
- [43] Uriel Singer, Adam Polyak, Thomas Hayes, Xi Yin, Jie An, Songyang Zhang, Qiyuan Hu, Harry Yang, Oron Ashual, Oran Gafni, et al. Make-a-video: Text-to-video generation without text-video data. arXiv preprint arXiv:2209.14792 , 2022. 3
- [44] Jascha Sohl-Dickstein, Eric Weiss, Niru Maheswaranathan, and Surya Ganguli. Deep unsupervised learning using nonequilibrium thermodynamics. In Proceedings of the 32nd International Conference on Machine Learning , pages 22562265, Lille, France, 2015. PMLR. 2
- [45] Yang Song, Jascha Sohl-Dickstein, Diederik P Kingma, Abhishek Kumar, Stefano Ermon, and Ben Poole. Score-based generative modeling through stochastic differential equations. arXiv preprint arXiv:2011.13456 , 2020. 2
- [46] Jiaxiang Tang, Zhaoxi Chen, Xiaokang Chen, Tengfei Wang, Gang Zeng, and Ziwei Liu. Lgm: Large multi-view gaussian model for high-resolution 3d content creation. arXiv preprint arXiv:2402.05054 , 2024. 2, 3, 4, 5, 6, 7
- [47] Shitao Tang, Jiacheng Chen, Dilin Wang, Chengzhou Tang, Fuyang Zhang, Yuchen Fan, Vikas Chandra, Yasutaka Furukawa, and Rakesh Ranjan. Mvdiffusion++: A dense high-resolution multi-view diffusion model for single or sparse-view 3d object reconstruction. arXiv preprint arXiv:2402.12712 , 2024. 2, 3
- [48] Dmitry Tochilkin, David Pankratz, Zexiang Liu, Zixuan Huang, Adam Letts, Yangguang Li, Ding Liang, Christian Laforte, Varun Jampani, and Yan-Pei Cao. Triposr: Fast 3d object reconstruction from a single image. arXiv preprint arXiv:2403.02151 , 2024. 6, 7
- [49] Vikram Voleti, Chun-Han Yao, Mark Boss, Adam Letts, David Pankratz, Dmitry Tochilkin, Christian Laforte, Robin

- Rombach, and Varun Jampani. Sv3d: Novel multi-view synthesis and 3d generation from a single image using latent video diffusion, 2024. 2, 3, 4, 6, 7, 8
- [50] Peng Wang and Yichun Shi. Imagedream: Image-prompt multi-view diffusion for 3d generation. arXiv preprint arXiv:2312.02201 , 2023. 8
- [51] Peng Wang, Lingjie Liu, Yuan Liu, Christian Theobalt, Taku Komura, and Wenping Wang. Neus: Learning neural implicit surfaces by volume rendering for multi-view reconstruction. arXiv preprint arXiv:2106.10689 , 2021. 3
- [52] Yaohui Wang, Xinyuan Chen, Xin Ma, Shangchen Zhou, Ziqi Huang, Yi Wang, Ceyuan Yang, Yinan He, Jiashuo Yu, Peiqing Yang, et al. Lavie: High-quality video generation with cascaded latent diffusion models. arXiv preprint arXiv:2309.15103 , 2023. 3
- [53] Zhengyi Wang, Yikai Wang, Yifei Chen, Chendong Xiang, Shuo Chen, Dajiang Yu, Chongxuan Li, Hang Su, and Jun Zhu. Crm: Single image to 3d textured mesh with convolutional reconstruction model. arXiv preprint arXiv:2403.05034 , 2024. 2, 3, 8
- [54] Tong Wu, Jiarui Zhang, Xiao Fu, Yuxin Wang, Jiawei Ren, Liang Pan, Wayne Wu, Lei Yang, Jiaqi Wang, Chen Qian, et al. Omniobject3d: Large-vocabulary 3d object dataset for realistic perception, reconstruction and generation. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition , pages 803-814, 2023. 2
- [55] Desai Xie, Jiahao Li, Hao Tan, Xin Sun, Zhixin Shu, Yi Zhou, Sai Bi, Sören Pirk, and Arie E Kaufman. Carve3d: Improving multi-view reconstruction consistency for diffusion models with rl finetuning. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition , pages 6369-6379, 2024. 2
- [56] Jiale Xu, Weihao Cheng, Yiming Gao, Xintao Wang, Shenghua Gao, and Ying Shan. Instantmesh: Efficient 3d mesh generation from a single image with sparse-view large reconstruction models. arXiv preprint arXiv:2404.07191 , 2024. 2, 3, 6, 7, 8
- [57] Yinghao Xu, Hao Tan, Fujun Luan, Sai Bi, Peng Wang, Jiahao Li, Zifan Shi, Kalyan Sunkavalli, Gordon Wetzstein, Zexiang Xu, et al. Dmv3d: Denoising multi-view diffusion using 3d large reconstruction model. arXiv preprint arXiv:2311.09217 , 2023. 3
- [58] Yinghao Xu, Zifan Shi, Wang Yifan, Hansheng Chen, Ceyuan Yang, Sida Peng, Yujun Shen, and Gordon Wetzstein. Grm: Large gaussian reconstruction model for efficient 3d reconstruction and generation. arXiv preprint arXiv:2403.14621 , 2024. 2, 3
- [59] Jiayu Yang, Ziang Cheng, Yunfei Duan, Pan Ji, and Hongdong Li. Consistnet: Enforcing 3d consistency for multi-view images diffusion. arXiv preprint arXiv:2310.10343 , 2023. 3
- [60] Xianggang Yu, Mutian Xu, Yidan Zhang, Haolin Liu, Chongjie Ye, Yushuang Wu, Zizheng Yan, Chenming Zhu, Zhangyang Xiong, Tianyou Liang, et al. Mvimgnet: A largescale dataset of multi-view images. In Proceedings of the IEEE/CVF conference on computer vision and pattern recognition , pages 9150-9161, 2023. 2, 3
- [61] Jia-Qi Zhang, Xiang Xu, Zhi-Meng Shen, Ze-Huan Huang, Yang Zhao, Yan-Pei Cao, Pengfei Wan, and Miao Wang.
- Write-an-animation: High-level text-based animation editing with character-scene interaction. In Computer Graphics Forum , pages 217-228. Wiley Online Library, 2021. 3
- [62] Richard Zhang, Phillip Isola, Alexei A Efros, Eli Shechtman, and Oliver Wang. The unreasonable effectiveness of deep features as a perceptual metric. In Proceedings of the IEEE conference on computer vision and pattern recognition , pages 586-595, 2018. 6
- [63] Chuanxia Zheng and Andrea Vedaldi. Free3d: Consistent novel view synthesis without 3d representation. arXiv preprint arXiv:2312.04551 , 2023. 3, 4
- [64] Zi-Xin Zou, Zhipeng Yu, Yuan-Chen Guo, Yangguang Li, Ding Liang, Yan-Pei Cao, and Song-Hai Zhang. Triplane meets gaussian splatting: Fast and generalizable singleview 3d reconstruction with transformers. arXiv preprint arXiv:2312.09147 , 2023. 3
- [65] Qi Zuo, Xiaodong Gu, Lingteng Qiu, Yuan Dong, Zhengyi Zhao, Weihao Yuan, Rui Peng, Siyu Zhu, Zilong Dong, Liefeng Bo, et al. Videomv: Consistent multi-view generation based on large video generative model. arXiv preprint arXiv:2403.12010 , 2024. 2, 3, 4, 6, 7