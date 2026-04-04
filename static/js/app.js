(function () {
  if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();
  }

  const questionsBuilder = document.getElementById("questions-builder");
  const addQuestionButton = document.getElementById("add-question-btn");
  const testBuilderForm = document.getElementById("test-builder-form");
  const questionsPayload = document.getElementById("questions-payload");

  const questionTemplate = (index) => `
    <div class="question-builder" data-question-index="${index}">
      <label>
        <span>${index + 1}-savol matni</span>
        <textarea data-role="question-text" rows="3" required></textarea>
      </label>
      <div class="grid-form">
        <label><span>A variant</span><input type="text" data-role="option" required></label>
        <label><span>B variant</span><input type="text" data-role="option" required></label>
        <label><span>C variant</span><input type="text" data-role="option" required></label>
        <label><span>D variant</span><input type="text" data-role="option" required></label>
      </div>
      <label>
        <span>To'g'ri javob</span>
        <select data-role="correct" required>
          <option value="">Tanlang</option>
          <option value="0">A</option>
          <option value="1">B</option>
          <option value="2">C</option>
          <option value="3">D</option>
        </select>
      </label>
    </div>
  `;

  const addQuestionBlock = () => {
    if (!questionsBuilder) return;
    const index = questionsBuilder.children.length;
    questionsBuilder.insertAdjacentHTML("beforeend", questionTemplate(index));
  };

  if (addQuestionButton) {
    addQuestionButton.addEventListener("click", addQuestionBlock);
  }

  if (questionsBuilder && !questionsBuilder.children.length) {
    addQuestionBlock();
  }

  if (testBuilderForm && questionsPayload) {
    testBuilderForm.addEventListener("submit", (event) => {
      const blocks = [...questionsBuilder.querySelectorAll("[data-question-index]")];
      const payload = blocks.map((block) => ({
        text: block.querySelector('[data-role="question-text"]').value.trim(),
        options: [...block.querySelectorAll('[data-role="option"]')].map((option) => option.value.trim()),
        correct_index: Number(block.querySelector('[data-role="correct"]').value),
      }));
      if (!payload.length) {
        event.preventDefault();
        return;
      }
      questionsPayload.value = JSON.stringify(payload);
    });
  }
})();
